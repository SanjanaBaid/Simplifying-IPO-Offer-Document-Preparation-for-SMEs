"""
Risk & Completeness Auditor API (Camp IV, Module 04).

Thin on top of handoff.py's compute_scorecard() — reuses the same Intake /
Drafting / Consistency / Risk Audit / Handoff scoring and gap_list rather than
recomputing any of it. What this module adds on top:

    1. An explicit Schedule VI clause-coverage count: for each of the 22
       seeded ScheduleVIFields, whether the promoter answered it at intake
       AND whether that clause number actually shows up in a drafted
       section's `schedule_vi_clause` citation. score_intake() in handoff.py
       only checks "answered" — it has no visibility into whether the answer
       ever made it into a draft. That gap matters here because SEBI's brief
       asks the solution to "flag gaps or inconsistencies", and "answered but
       never drafted" is exactly that kind of gap.
    2. The flat gap_list regrouped into audit-shaped sections (Statutory
       Coverage, Drafting Completeness, Risk Specificity, Financial
       Consistency, Handoff Readiness) instead of one undifferentiated list,
       since that's how a merchant banker actually triages an audit.

Endpoints:
    GET /audit/report?company_id=...

Wire into main.py:
    from audit import router as audit_router
    app.include_router(audit_router)
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_promoter
from database import get_db
from models import Company, IntakeSession, Promoter, ScheduleVIField
from handoff import _latest_drafts_by_section, compute_scorecard

router = APIRouter(prefix="/audit", tags=["audit"])

# Maps handoff.py's module names onto the audit-report section groupings.
MODULE_TO_SECTION = {
    "Intake": "Statutory Coverage",
    "Drafting": "Drafting Completeness",
    "Consistency": "Financial Consistency",
    "Risk Audit": "Risk Specificity",
    "Merchant Banker Handoff": "Handoff Readiness",
}
SECTION_ORDER = [
    "Statutory Coverage",
    "Drafting Completeness",
    "Risk Specificity",
    "Financial Consistency",
    "Handoff Readiness",
]


def compute_clause_coverage(db: Session, company_id: str) -> Dict:
    """For every seeded Schedule VI field: was it answered at intake, and did
    that clause number actually get cited in a drafted section? Answered-but-
    never-cited is a real gap score_intake() can't see, since it only checks
    whether an IntakeSession row has response_text."""
    fields = db.query(ScheduleVIField).all()
    if not fields:
        return {
            "total_fields": 0,
            "answered_count": 0,
            "cited_count": 0,
            "coverage_pct": 0,
            "gaps": [],
        }

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

    latest_drafts = _latest_drafts_by_section(db, company_id)
    cited_clause_blob = " | ".join(
        draft.schedule_vi_clause for draft in latest_drafts.values() if draft.schedule_vi_clause
    )

    gaps: List[Dict] = []
    cited_count = 0
    for field in fields:
        answered = field.field_key in answered_keys
        cited = bool(cited_clause_blob) and field.clause_number in cited_clause_blob
        if cited:
            cited_count += 1

        if not answered:
            continue  # already surfaced as an Intake gap by handoff.build_gap_list
        if not cited:
            gaps.append(
                {
                    "priority": "MEDIUM",
                    "module": "Intake",
                    "description": (
                        f"'{field.plain_language_prompt}' ({field.clause_number}) was answered at "
                        f"intake but hasn't been cited in any drafted section yet."
                    ),
                }
            )

    coverage_pct = round(100 * cited_count / len(fields)) if fields else 0
    return {
        "total_fields": len(fields),
        "answered_count": len(answered_keys),
        "cited_count": cited_count,
        "coverage_pct": coverage_pct,
        "gaps": gaps,
    }


def build_audit_sections(gap_list: List[Dict], clause_gaps: List[Dict]) -> List[Dict]:
    """Regroup handoff.py's flat gap_list (plus the clause-coverage gaps
    computed above) into the five audit-report sections, each carrying its
    own status so the UI can render a clear/partial/gap-found card per
    section without re-deriving it from raw gaps."""
    buckets: Dict[str, List[Dict]] = {name: [] for name in SECTION_ORDER}

    for gap in gap_list + clause_gaps:
        section = MODULE_TO_SECTION.get(gap["module"], "Statutory Coverage")
        buckets[section].append(gap)

    sections = []
    for name in SECTION_ORDER:
        items = buckets[name]
        if not items:
            status = "clear"
        elif any(g["priority"] == "HIGH" for g in items):
            status = "flag"
        else:
            status = "pending"
        sections.append({"name": name, "status": status, "items": items})
    return sections


class ClauseCoverageOut(BaseModel):
    total_fields: int
    answered_count: int
    cited_count: int
    coverage_pct: int


class AuditGapOut(BaseModel):
    priority: str
    module: str
    description: str


class AuditSectionOut(BaseModel):
    name: str
    status: str
    items: List[AuditGapOut]


class ModuleScoreOut(BaseModel):
    module: str
    score: int
    max: int
    note: str


class AuditReportOut(BaseModel):
    company_id: str
    company_name: str
    total_score: int
    modules: List[ModuleScoreOut]
    clause_coverage: ClauseCoverageOut
    sections: List[AuditSectionOut]


@router.get("/report", response_model=AuditReportOut)
def get_audit_report(
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
    clause_coverage = compute_clause_coverage(db, company_id)
    sections = build_audit_sections(result["gap_list"], clause_coverage["gaps"])

    return AuditReportOut(
        company_id=result["company_id"],
        company_name=result["company_name"],
        total_score=result["total_score"],
        modules=[ModuleScoreOut(**m) for m in result["modules"]],
        clause_coverage=ClauseCoverageOut(
            total_fields=clause_coverage["total_fields"],
            answered_count=clause_coverage["answered_count"],
            cited_count=clause_coverage["cited_count"],
            coverage_pct=clause_coverage["coverage_pct"],
        ),
        sections=[AuditSectionOut(**s) for s in sections],
    )