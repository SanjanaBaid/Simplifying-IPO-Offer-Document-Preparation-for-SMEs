
import re
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Company, DraftSection, ExtractedFinancialLineItem, FinancialDocument

router = APIRouter(prefix="/consistency", tags=["consistency"])

DEFAULT_MATERIALITY_THRESHOLD_PCT = 1.0


_CLAIM_RE = re.compile(
    r"(?P<label>(?:[A-Za-z][A-Za-z&/'.-]*\s+){1,8}?)"
    r"(?:is|was|of|at|stood at|to|:|were|amounts?\s+to)?\s*"
    r"(?:₹|Rs\.?|INR)?\s*"
    r"(?P<value>\d[\d,]*(?:\.\d+)?)\s*"
    r"(?P<pct>%)?",
    re.IGNORECASE,
)

STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "for", "to", "and", "or", "is", "was",
    "were", "at", "as", "by", "with", "its", "their", "this", "that", "has",
    "have", "had", "be", "been", "being", "company's", "companys",
}


def _tokenize(label: str) -> set:
    words = re.findall(r"[a-z]+", label.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def _parse_number(raw: str) -> Optional[float]:
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def extract_numeric_claims(text: str) -> List[Dict]:
    """Pull (label, value, is_percent) triples out of narrative text."""
    claims = []
    for match in _CLAIM_RE.finditer(text):
        value = _parse_number(match.group("value"))
        if value is None:
            continue
        label = match.group("label").strip()
        boundary = max(label.rfind(". "), label.rfind("\n"))
        if boundary != -1:
            label = label[boundary + 1:].strip(" .")
        if len(label) < 3:
            continue
        if "cl." in label.lower() or "sch." in label.lower():
            continue
        claims.append(
            {
                "label": label,
                "value": value,
                "is_percent": bool(match.group("pct")),
                "snippet": text[max(0, match.start() - 20): match.end() + 10].strip(),
            }
        )
    return claims


def _best_line_item_match(claim_label: str, line_items: List[ExtractedFinancialLineItem]):
    """Token-overlap fuzzy match between a claim's label and financial line-item labels."""
    claim_tokens = _tokenize(claim_label)
    if not claim_tokens:
        return None, 0.0

    best_item, best_score = None, 0.0
    for item in line_items:
        item_tokens = _tokenize(item.label or "")
        if not item_tokens:
            continue
        overlap = len(claim_tokens & item_tokens)
        if overlap == 0:
            continue
        score = overlap / min(len(claim_tokens), len(item_tokens))
        if score > best_score:
            best_item, best_score = item, score
    return best_item, best_score


MATCH_SCORE_THRESHOLD = 0.5


def relative_variance_pct(claimed: float, actual: float) -> float:
    if actual == 0:
        return 0.0 if claimed == 0 else 100.0
    return abs(claimed - actual) / abs(actual) * 100.0




def run_crossfoot_checks(line_items: List[ExtractedFinancialLineItem], threshold_pct: float) -> List[Dict]:
    """Group line items by period; where a label reads as a 'total', verify
    it sums its non-total siblings from the same period."""
    by_period: Dict[Optional[str], List[ExtractedFinancialLineItem]] = {}
    for item in line_items:
        by_period.setdefault(item.period, []).append(item)

    results = []
    for period, items in by_period.items():
        totals = [i for i in items if i.label and "total" in i.label.lower()]
        non_totals = [i for i in items if i not in totals]
        if not totals or not non_totals:
            continue
        computed_sum = sum(i.value for i in non_totals if i.value is not None)
        for total_item in totals:
            if total_item.value is None:
                continue
            variance = relative_variance_pct(computed_sum, total_item.value)
            results.append(
                {
                    "period": period or "period unspecified",
                    "total_label": total_item.label,
                    "reported_total": total_item.value,
                    "computed_sum": round(computed_sum, 2),
                    "component_labels": [i.label for i in non_totals],
                    "variance_pct": round(variance, 2),
                    "flagged": variance > threshold_pct,
                }
            )
    return results



def run_ratio_checks(line_items: List[ExtractedFinancialLineItem]) -> List[Dict]:
    def find(*keywords):
        for item in line_items:
            label = (item.label or "").lower()
            if all(k in label for k in keywords) and item.value is not None:
                return item
        return None

    checks = []

    authorized = find("authoris", "capital") or find("authoriz", "capital")
    paid_up = find("paid", "capital") or find("paid-up", "capital")
    if authorized and paid_up:
        flagged = paid_up.value > authorized.value
        checks.append(
            {
                "check_name": "Paid-up capital vs. authorized capital",
                "description": (
                    f"Paid-up capital ({paid_up.value}) should not exceed authorized "
                    f"capital ({authorized.value})."
                ),
                "flagged": flagged,
                "detail": "Paid-up capital exceeds authorized capital — structurally impossible."
                if flagged
                else "Within bounds.",
            }
        )

    return checks



class NumericClaimOut(BaseModel):
    draft_section: str
    draft_version: int
    schedule_vi_clause: Optional[str] = None
    claimed_label: str
    claimed_value: float
    is_percent: bool
    snippet: str
    status: str  # "match" | "mismatch" | "unmatched"
    matched_line_item_label: Optional[str] = None
    matched_line_item_value: Optional[float] = None
    matched_line_item_period: Optional[str] = None
    variance_pct: Optional[float] = None
    match_confidence: Optional[float] = None


class CrossFootOut(BaseModel):
    period: str
    total_label: str
    reported_total: float
    computed_sum: float
    component_labels: List[str]
    variance_pct: float
    flagged: bool


class RatioCheckOut(BaseModel):
    check_name: str
    description: str
    flagged: bool
    detail: str


class ConsistencyCheckOut(BaseModel):
    company_id: str
    materiality_threshold_pct: float
    numeric_claims: List[NumericClaimOut]
    crossfoot_checks: List[CrossFootOut]
    ratio_checks: List[RatioCheckOut]
    flagged_count: int
    sections_checked: List[str]




@router.post("/check", response_model=ConsistencyCheckOut)
def check_consistency(
    company_id: str,
    materiality_threshold_pct: float = DEFAULT_MATERIALITY_THRESHOLD_PCT,
    db: Session = Depends(get_db),
):
    """Run the full consistency check for a company: numeric-claim matching,
    cross-foot checks, and structural ratio checks."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Unknown company_id: {company_id}")


    all_drafts = (
        db.query(DraftSection)
        .filter(DraftSection.company_id == company_id)
        .order_by(DraftSection.section_name, DraftSection.version.desc())
        .all()
    )
    latest_by_section: Dict[str, DraftSection] = {}
    for draft in all_drafts:
        if draft.section_name not in latest_by_section:
            latest_by_section[draft.section_name] = draft

    if not latest_by_section:
        raise HTTPException(
            status_code=404,
            detail="No drafted sections found for this company yet — generate a draft via /drafting/generate first.",
        )

    line_items = (
        db.query(ExtractedFinancialLineItem)
        .join(FinancialDocument, FinancialDocument.id == ExtractedFinancialLineItem.document_id)
        .filter(FinancialDocument.company_id == company_id)
        .all()
    )

    numeric_claims: List[NumericClaimOut] = []
    for draft in latest_by_section.values():
        if not draft.content:
            continue
        for claim in extract_numeric_claims(draft.content):
            best_item, score = _best_line_item_match(claim["label"], line_items)

            if best_item is None or score < MATCH_SCORE_THRESHOLD:
                status = "unmatched"
                matched_label = matched_value = matched_period = variance = None
                confidence = round(score, 2) if best_item else None
            else:
                matched_label = best_item.label
                matched_value = best_item.value
                matched_period = best_item.period
                confidence = round(score, 2)
                variance = round(relative_variance_pct(claim["value"], best_item.value), 2) if best_item.value is not None else None
                status = "mismatch" if (variance is not None and variance > materiality_threshold_pct) else "match"

            numeric_claims.append(
                NumericClaimOut(
                    draft_section=draft.section_name,
                    draft_version=draft.version,
                    schedule_vi_clause=draft.schedule_vi_clause,
                    claimed_label=claim["label"],
                    claimed_value=claim["value"],
                    is_percent=claim["is_percent"],
                    snippet=claim["snippet"],
                    status=status,
                    matched_line_item_label=matched_label,
                    matched_line_item_value=matched_value,
                    matched_line_item_period=matched_period,
                    variance_pct=variance,
                    match_confidence=confidence,
                )
            )

    crossfoot_raw = run_crossfoot_checks(line_items, materiality_threshold_pct)
    crossfoot_checks = [CrossFootOut(**c) for c in crossfoot_raw]

    ratio_raw = run_ratio_checks(line_items)
    ratio_checks = [RatioCheckOut(**r) for r in ratio_raw]

    flagged_count = (
        sum(1 for c in numeric_claims if c.status == "mismatch")
        + sum(1 for c in crossfoot_checks if c.flagged)
        + sum(1 for r in ratio_checks if r.flagged)
    )

    return ConsistencyCheckOut(
        company_id=company_id,
        materiality_threshold_pct=materiality_threshold_pct,
        numeric_claims=numeric_claims,
        crossfoot_checks=crossfoot_checks,
        ratio_checks=ratio_checks,
        flagged_count=flagged_count,
        sections_checked=list(latest_by_section.keys()),
    )