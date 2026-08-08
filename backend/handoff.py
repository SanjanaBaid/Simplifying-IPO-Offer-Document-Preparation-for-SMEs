import io
import textwrap
from datetime import datetime
from typing import Dict, List, Literal, Optional

import fitz
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_promoter
from database import get_db
from models import (
    Company,
    DraftSection,
    ExtractedFinancialLineItem,
    FinancialDocument,
    IntakeSession,
    Promoter,
    ScheduleVIField,
)
from classifier import RISK_FACTORS_SECTION_NAME, classify_item
from consistency import (
    DEFAULT_MATERIALITY_THRESHOLD_PCT,
    _best_line_item_match,
    MATCH_SCORE_THRESHOLD,
    extract_numeric_claims,
    relative_variance_pct,
    run_crossfoot_checks,
    run_ratio_checks,
)

router = APIRouter(prefix="/handoff", tags=["handoff"])

MODULE_MAX = 20
CORE_SECTIONS = [
    "General Information",
    "Business Overview",
    "Objects of the Issue",
    "Risk Factors",
    "Capital Structure",
    "Management & Key Managerial Personnel",
    "Statutory Approvals & Borrowings",
]

PRIORITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _is_stub_draft(content: Optional[str]) -> bool:
    """True if this draft's content is drafting.py's GROQ_API_KEY-missing
    placeholder rather than real (LLM-generated or promoter-edited) text.
    Scoring functions below all need this: a stub has no
    "[NEEDS PROMOTER INPUT" gap tags and no boilerplate phrases, so without
    this check it silently scores as a clean, fully-drafted section instead
    of the "nothing real generated yet" state it actually is."""
    return bool(content) and content.strip().startswith("[STUB DRAFT")


def _latest_drafts_by_section(db: Session, company_id: str) -> Dict[str, DraftSection]:
    all_drafts = (
        db.query(DraftSection)
        .filter(DraftSection.company_id == company_id)
        .order_by(DraftSection.section_name, DraftSection.version.desc())
        .all()
    )
    latest: Dict[str, DraftSection] = {}
    for draft in all_drafts:
        if draft.section_name not in latest:
            latest[draft.section_name] = draft
    return latest


def _financial_line_items(db: Session, company_id: str) -> List[ExtractedFinancialLineItem]:
    return (
        db.query(ExtractedFinancialLineItem)
        .join(FinancialDocument, FinancialDocument.id == ExtractedFinancialLineItem.document_id)
        .filter(FinancialDocument.company_id == company_id)
        .all()
    )


def _run_consistency(latest_drafts: Dict[str, DraftSection], line_items):
    numeric_claims = []
    for draft in latest_drafts.values():
        if not draft.content:
            continue
        for claim in extract_numeric_claims(draft.content):
            best_item, score = _best_line_item_match(claim["label"], line_items)
            if best_item is None or score < MATCH_SCORE_THRESHOLD:
                status = "unmatched"
                variance = None
            else:
                variance = (
                    round(relative_variance_pct(claim["value"], best_item.value), 2)
                    if best_item.value is not None
                    else None
                )
                status = "mismatch" if (variance is not None and variance > DEFAULT_MATERIALITY_THRESHOLD_PCT) else "match"
            numeric_claims.append(
                {
                    "draft_section": draft.section_name,
                    "claimed_label": claim["label"],
                    "claimed_value": claim["value"],
                    "status": status,
                    "matched_line_item_label": best_item.label if best_item else None,
                    "matched_line_item_value": best_item.value if best_item else None,
                    "variance_pct": variance,
                }
            )

    crossfoot = run_crossfoot_checks(line_items, DEFAULT_MATERIALITY_THRESHOLD_PCT)
    ratio = run_ratio_checks(line_items)
    return numeric_claims, crossfoot, ratio


def score_intake(db: Session, company_id: str) -> Dict:
    total_fields = db.query(ScheduleVIField).count()
    if total_fields == 0:
        return {"module": "Intake", "score": 0, "max": MODULE_MAX, "note": "No Schedule VI fields seeded yet."}

    answered = (
        db.query(IntakeSession)
        .filter(
            IntakeSession.company_id == company_id,
            IntakeSession.response_text.isnot(None),
            IntakeSession.response_text != "",
        )
        .count()
    )
    score = round(MODULE_MAX * answered / total_fields)
    return {
        "module": "Intake",
        "score": score,
        "max": MODULE_MAX,
        "note": f"{answered} of {total_fields} Schedule VI fields answered.",
    }


def score_drafting(latest_drafts: Dict[str, DraftSection]) -> Dict:
    per_section_max = MODULE_MAX / len(CORE_SECTIONS)
    total = 0.0
    notes = []
    for section_name in CORE_SECTIONS:
        draft = latest_drafts.get(section_name)
        if not draft or not draft.content:
            notes.append(f"{section_name}: not drafted")
            continue
        if _is_stub_draft(draft.content) and not draft.is_manual_edit:
            notes.append(f"{section_name}: stub only (GROQ_API_KEY not set)")
            continue
        gap_count = draft.content.upper().count("[NEEDS PROMOTER INPUT")
        section_score = max(0.0, per_section_max - min(per_section_max, gap_count * 2))
        total += section_score
        notes.append(f"{section_name}: v{draft.version}, {gap_count} gap(s) flagged")
    return {"module": "Drafting", "score": round(total), "max": MODULE_MAX, "note": "; ".join(notes)}


def score_consistency(numeric_claims: List[Dict], crossfoot: List[Dict], ratio: List[Dict], has_drafts: bool) -> Dict:
    if not has_drafts:
        return {"module": "Consistency", "score": 0, "max": MODULE_MAX, "note": "No drafted sections to check yet."}

    total_checks = len(numeric_claims) + len(crossfoot) + len(ratio)
    if total_checks == 0:
        return {
            "module": "Consistency",
            "score": 10,
            "max": MODULE_MAX,
            "note": "Drafted, but no checkable numeric claims found yet.",
        }

    flagged = (
        sum(1 for c in numeric_claims if c["status"] == "mismatch")
        + sum(1 for c in crossfoot if c["flagged"])
        + sum(1 for r in ratio if r["flagged"])
    )
    score = round(MODULE_MAX * (total_checks - flagged) / total_checks)
    return {
        "module": "Consistency",
        "score": score,
        "max": MODULE_MAX,
        "note": f"{flagged} of {total_checks} checks flagged.",
    }


def score_risk_audit(latest_drafts: Dict[str, DraftSection]) -> Dict:
    risk_draft = latest_drafts.get(RISK_FACTORS_SECTION_NAME)
    if not risk_draft or not risk_draft.content:
        return {"module": "Risk Audit", "score": 0, "max": MODULE_MAX, "note": "No Risk Factors draft yet."}
    if _is_stub_draft(risk_draft.content) and not risk_draft.is_manual_edit:
        return {
            "module": "Risk Audit",
            "score": 0,
            "max": MODULE_MAX,
            "note": "Risk Factors draft is a stub (GROQ_API_KEY not set) — nothing real to audit yet.",
        }

    paragraphs = [p.strip() for p in risk_draft.content.split("\n\n") if p.strip()]
    if not paragraphs:
        return {"module": "Risk Audit", "score": 10, "max": MODULE_MAX, "note": "Drafted, but nothing to classify."}

    items = [classify_item(p) for p in paragraphs]
    flagged = sum(1 for i in items if i["needs_promoter_input"])
    score = round(MODULE_MAX * (len(items) - flagged) / len(items))
    return {
        "module": "Risk Audit",
        "score": score,
        "max": MODULE_MAX,
        "note": f"{flagged} of {len(items)} risk factors need promoter input.",
    }


def score_handoff_readiness(
    company: Company,
    has_financials: bool,
    latest_drafts: Dict[str, DraftSection],
    consistency_score: int,
) -> Dict:
    profile_fields = [company.name, company.sector, company.proposed_issue_size_cr]
    profile_present = sum(1 for f in profile_fields if f not in (None, ""))
    profile_pts = 5 * profile_present / len(profile_fields)

    financials_pts = 5 if has_financials else 0

    drafted_pts = 5 * sum(
        1 for s in CORE_SECTIONS
        if s in latest_drafts and not (_is_stub_draft(latest_drafts[s].content) and not latest_drafts[s].is_manual_edit)
    ) / len(CORE_SECTIONS)

    consistency_pts = 5 * consistency_score / MODULE_MAX

    total = round(profile_pts + financials_pts + drafted_pts + consistency_pts)
    return {
        "module": "Merchant Banker Handoff",
        "score": min(MODULE_MAX, total),
        "max": MODULE_MAX,
        "note": "Company profile, financials, drafts, and consistency all roll up into handoff readiness.",
    }


import re

_GAP_TAG_RE = re.compile(r"\[NEEDS PROMOTER INPUT:?\s*([^\]\n]*)\]", re.IGNORECASE)


def build_gap_list(
    db: Session,
    company_id: str,
    latest_drafts: Dict[str, DraftSection],
    numeric_claims: List[Dict],
    crossfoot: List[Dict],
    ratio: List[Dict],
    has_financials: bool,
) -> List[Dict]:
    gaps: List[Dict] = []

    for section_name, draft in latest_drafts.items():
        if not draft.content:
            continue
        for match in _GAP_TAG_RE.finditer(draft.content):
            detail = match.group(1).strip()
            gaps.append(
                {
                    "priority": "HIGH",
                    "module": "Drafting",
                    "description": f"{section_name}: promoter input needed" + (f" — {detail}" if detail else ""),
                }
            )

    for claim in numeric_claims:
        if claim["status"] != "mismatch":
            continue
        gaps.append(
            {
                "priority": "HIGH",
                "module": "Consistency",
                "description": (
                    f"{claim['draft_section']}: \"{claim['claimed_label']}\" drafted as {claim['claimed_value']} "
                    f"vs. financials {claim['matched_line_item_value']} ({claim['variance_pct']}% variance)"
                ),
            }
        )

    for r in ratio:
        if r["flagged"]:
            gaps.append({"priority": "HIGH", "module": "Consistency", "description": r["detail"]})

    for c in crossfoot:
        if c["flagged"]:
            gaps.append(
                {
                    "priority": "MEDIUM",
                    "module": "Consistency",
                    "description": (
                        f"{c['total_label']} ({c['period']}) doesn't foot — {c['variance_pct']}% variance"
                    ),
                }
            )

    risk_draft = latest_drafts.get(RISK_FACTORS_SECTION_NAME)
    if risk_draft and risk_draft.content:
        for p in [p.strip() for p in risk_draft.content.split("\n\n") if p.strip()]:
            result = classify_item(p)
            if result["needs_promoter_input"]:
                snippet = p if len(p) <= 140 else p[:137] + "..."
                gaps.append({"priority": "MEDIUM", "module": "Risk Audit", "description": snippet})

    total_fields = db.query(ScheduleVIField).all()
    answered_keys = {
        row.field_key
        for row in (
            db.query(ScheduleVIField.field_key)
            .join(IntakeSession, IntakeSession.field_id == ScheduleVIField.id)
            .filter(
                IntakeSession.company_id == company_id,
                IntakeSession.response_text.isnot(None),
                IntakeSession.response_text != "",
            )
            .all()
        )
    }
    for field in total_fields:
        if field.field_key not in answered_keys:
            gaps.append(
                {
                    "priority": "LOW",
                    "module": "Intake",
                    "description": f"'{field.plain_language_prompt}' not yet answered ({field.field_key})",
                }
            )

    if not has_financials:
        gaps.append({"priority": "LOW", "module": "Handoff", "description": "No financial statements uploaded yet."})

    gaps.sort(key=lambda g: PRIORITY_RANK.get(g["priority"], 99))
    return gaps


def compute_scorecard(db: Session, company: Company) -> Dict:
    latest_drafts = _latest_drafts_by_section(db, company.id)
    line_items = _financial_line_items(db, company.id)
    has_financials = len(line_items) > 0

    numeric_claims, crossfoot, ratio = _run_consistency(latest_drafts, line_items)

    intake = score_intake(db, company.id)
    drafting = score_drafting(latest_drafts)
    consistency = score_consistency(numeric_claims, crossfoot, ratio, has_drafts=bool(latest_drafts))
    risk_audit = score_risk_audit(latest_drafts)
    handoff = score_handoff_readiness(company, has_financials, latest_drafts, consistency["score"])

    modules = [intake, drafting, consistency, risk_audit, handoff]
    total_score = sum(m["score"] for m in modules)

    gap_list = build_gap_list(db, company.id, latest_drafts, numeric_claims, crossfoot, ratio, has_financials)

    return {
        "company_id": company.id,
        "company_name": company.name,
        "modules": modules,
        "total_score": total_score,
        "gap_list": gap_list,
        "latest_drafts": latest_drafts,
    }


class ModuleScoreOut(BaseModel):
    module: str
    score: int
    max: int
    note: str


class GapItemOut(BaseModel):
    priority: str
    module: str
    description: str


class ScorecardOut(BaseModel):
    company_id: str
    company_name: str
    modules: List[ModuleScoreOut]
    total_score: int
    gap_list: List[GapItemOut]


class _PdfWriter:

    PAGE_W, PAGE_H, MARGIN = 595, 842, 40

    def __init__(self):
        self.doc = fitz.open()
        self.y = 0
        self._new_page()

    def _new_page(self):
        self.page = self.doc.new_page(width=self.PAGE_W, height=self.PAGE_H)
        self.y = self.MARGIN

    def _ensure(self, needed: float):
        if self.y + needed > self.PAGE_H - self.MARGIN:
            self._new_page()

    def heading(self, text: str, size: float = 16):
        self._ensure(size + 10)
        self.page.insert_text((self.MARGIN, self.y + size), text, fontsize=size, fontname="helv")
        self.y += size + 10

    def subheading(self, text: str, size: float = 11.5):
        self._ensure(size + 8)
        self.page.insert_text((self.MARGIN, self.y + size), text, fontsize=size, fontname="helv")
        self.y += size + 8

    def paragraph(self, text: str, size: float = 9.5, line_gap: float = 13, wrap_chars: int = 100):
        for raw_line in (text or "").split("\n"):
            wrapped = textwrap.wrap(raw_line, width=wrap_chars) or [""]
            for line in wrapped:
                self._ensure(line_gap)
                self.page.insert_text((self.MARGIN, self.y + size), line, fontsize=size, fontname="helv")
                self.y += line_gap
        self.y += 4

    def spacer(self, height: float = 8):
        self.y += height

    def to_bytes(self) -> bytes:
        return self.doc.tobytes()


def render_pdf(package: Dict) -> bytes:
    w = _PdfWriter()

    w.heading(f"{package['company_name']} — Merchant Banker Handoff Package")
    w.subheading(f"Generated {package['generated_at']} · Completeness score {package['total_score']}/100")
    w.spacer()

    w.subheading("Completeness Scorecard")
    for m in package["modules"]:
        w.paragraph(f"{m['module']}: {m['score']}/{m['max']} — {m['note']}")
    w.spacer()

    w.subheading(f"Prioritised Gap List ({len(package['gap_list'])})")
    if package["gap_list"]:
        for g in package["gap_list"]:
            w.paragraph(f"[{g['priority']}] {g['module']}: {g['description']}")
    else:
        w.paragraph("No outstanding gaps.")
    w.spacer()

    w.subheading("Drafted Sections")
    for section in package["draft_sections"]:
        w.spacer()
        w.subheading(f"{section['section_name']} (v{section['version']})", size=12.5)
        if section.get("schedule_vi_clause"):
            w.paragraph(f"Cites: {section['schedule_vi_clause']}", size=8.5)
        w.paragraph(section.get("content") or "(empty)")

    return w.to_bytes()


@router.get("/scorecard", response_model=ScorecardOut)
def get_scorecard(
    company_id: str,
    current: Promoter = Depends(get_current_promoter),
    db: Session = Depends(get_db),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Unknown company_id: {company_id}")
    if company.promoter_id != current.id:
        raise HTTPException(status_code=403, detail="You don't have access to this company.")

    result = compute_scorecard(db, company)

    company.completeness_score = result["total_score"]
    db.commit()

    return ScorecardOut(
        company_id=result["company_id"],
        company_name=result["company_name"],
        modules=[ModuleScoreOut(**m) for m in result["modules"]],
        total_score=result["total_score"],
        gap_list=[GapItemOut(**g) for g in result["gap_list"]],
    )


@router.post("/export")
def export_handoff(
    company_id: str,
    export_format: Literal["pdf", "json"] = "json",
    current: Promoter = Depends(get_current_promoter),
    db: Session = Depends(get_db),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Unknown company_id: {company_id}")
    if company.promoter_id != current.id:
        raise HTTPException(status_code=403, detail="You don't have access to this company.")

    scorecard = compute_scorecard(db, company)
    company.completeness_score = scorecard["total_score"]
    db.commit()

    draft_sections = [
        {
            "section_name": draft.section_name,
            "version": draft.version,
            "schedule_vi_clause": draft.schedule_vi_clause,
            "content": draft.content,
        }
        for draft in scorecard["latest_drafts"].values()
    ]

    package = {
        "company_id": company.id,
        "company_name": company.name,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_score": scorecard["total_score"],
        "modules": scorecard["modules"],
        "gap_list": scorecard["gap_list"],
        "draft_sections": draft_sections,
    }

    if export_format == "json":
        return package

    pdf_bytes = render_pdf(package)
    filename = f"{company.name.replace(' ', '_')}_handoff.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )