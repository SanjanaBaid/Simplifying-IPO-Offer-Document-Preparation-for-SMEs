"""
Risk-Factor Classifier API (Phase 2, Step 9).

Splits a company's latest drafted "Risk Factors" section into individual risk items
(one per paragraph, matching how drafting.py's prompt asks the LLM to draft them),
then classifies each item as boilerplate or specific using two signals:

  1. Rule-based boilerplate phrase detection — a fixed list of generic risk-factor
     phrases that show up in almost every SME DRHP regardless of the actual company
     (e.g. "there can be no assurance that", "general economic conditions").
  2. LLM specificity scoring — asks the LLM to score 0-100 how specific this risk is
     to *this* company (quantified, named suppliers/customers/plants, etc.) vs. how
     generic/industry-boilerplate it reads.

An item is flagged ("needs promoter input") if either signal says it's generic. This
mirrors drafting.py's own [NEEDS PROMOTER INPUT] convention, so the two modules speak
the same language.

Draft versioning itself is already handled in drafting.py (Step 7) — every /drafting/generate
call already saves a new DraftSection version. This module only reads the latest version;
it doesn't write new draft versions.

Uses the same GROQ_API_KEY / stub-fallback pattern as drafting.py, so this endpoint is
testable in /docs with or without a real key.
"""

import os
import re
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Company, DraftSection

router = APIRouter(prefix="/classifier", tags=["classifier"])

RISK_FACTORS_SECTION_NAME = "Risk Factors"



BOILERPLATE_PHRASES = [
    "there can be no assurance that",
    "general economic conditions",
    "factors beyond our control",
    "may adversely affect",
    "could materially and adversely affect",
    "risks inherent in",
    "risks inherent to",
    "intense competition in the industry",
    "the industry is cyclical",
    "changes in government policies",
    "regulatory changes",
    "no assurance can be given",
    "subject to various risks",
    "may be affected by a number of factors",
]

_BOILERPLATE_RE = re.compile(
    "|".join(re.escape(p) for p in BOILERPLATE_PHRASES), re.IGNORECASE
)


_QUANTIFIED_RE = re.compile(r"(\d+(\.\d+)?\s*%|₹\s?[\d,]+|\brs\.?\s?[\d,]+)", re.IGNORECASE)


def rule_based_flag(text: str) -> Dict:
    matched = _BOILERPLATE_RE.findall(text)
    matched_unique = sorted({m.lower() for m in matched})
    is_quantified = bool(_QUANTIFIED_RE.search(text))
    return {
        "matched_phrases": matched_unique,
        "is_boilerplate": len(matched_unique) > 0,
        "is_quantified": is_quantified,
    }



DRAFTING_LLM_MODEL = os.getenv("DRAFTING_LLM_MODEL", "llama-3.3-70b-versatile")

_SPECIFICITY_SYSTEM_PROMPT = """You score how SPECIFIC a single SME DRHP risk factor is to the \
company that wrote it, versus how generic/boilerplate it reads. Specific risk factors name \
actual figures, percentages, suppliers, customers, plants, or dates. Generic risk factors \
could be copy-pasted into any company's offer document unchanged.

Respond with ONLY a number from 0 to 100 (0 = pure boilerplate, 100 = highly specific and \
quantified). No words, no explanation, just the number."""


def llm_specificity_score(text: str) -> Optional[int]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=DRAFTING_LLM_MODEL,
            max_tokens=10,
            messages=[
                {"role": "system", "content": _SPECIFICITY_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        raw = response.choices[0].message.content.strip()
        match = re.search(r"\d+", raw)
        if not match:
            return None
        return max(0, min(100, int(match.group())))
    except Exception:
        return None


def fallback_specificity_score(text: str, rule_result: Dict) -> int:
    """Used when no GROQ_API_KEY is set. Cheap heuristic, clearly not as good as the
    LLM score — the classification output notes which method was used."""
    score = 50
    if rule_result["is_boilerplate"]:
        score -= 30
    if rule_result["is_quantified"]:
        score += 30
    if len(text) < 60:
        score -= 10
    return max(0, min(100, score))


SPECIFICITY_FLAG_THRESHOLD = 50


def classify_item(text: str) -> Dict:
    rule_result = rule_based_flag(text)
    llm_score = llm_specificity_score(text)
    used_llm = llm_score is not None
    score = llm_score if used_llm else fallback_specificity_score(text, rule_result)

    needs_promoter_input = rule_result["is_boilerplate"] or score < SPECIFICITY_FLAG_THRESHOLD

    return {
        "text": text,
        "matched_phrases": rule_result["matched_phrases"],
        "specificity_score": score,
        "scored_with_llm": used_llm,
        "needs_promoter_input": needs_promoter_input,
    }




class RiskItemOut(BaseModel):
    text: str
    matched_phrases: List[str]
    specificity_score: int
    scored_with_llm: bool
    needs_promoter_input: bool


class ClassifyRisksOut(BaseModel):
    company_id: str
    draft_section_id: str
    version: int
    items: List[RiskItemOut]
    flagged_count: int




@router.post("/classify-risks", response_model=ClassifyRisksOut)
def classify_risks(company_id: str, db: Session = Depends(get_db)):
    """Classify the latest drafted Risk Factors section for a company. Split into
    one item per paragraph (matching how drafting.py prompts the LLM to draft
    each risk as its own paragraph)."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Unknown company_id: {company_id}")

    latest_draft = (
        db.query(DraftSection)
        .filter(DraftSection.company_id == company_id, DraftSection.section_name == RISK_FACTORS_SECTION_NAME)
        .order_by(DraftSection.version.desc())
        .first()
    )
    if not latest_draft or not latest_draft.content:
        raise HTTPException(
            status_code=404,
            detail="No Risk Factors draft found for this company yet — generate one via /drafting/generate first.",
        )

    paragraphs = [p.strip() for p in latest_draft.content.split("\n\n") if p.strip()]
    items = [classify_item(p) for p in paragraphs]
    flagged_count = sum(1 for i in items if i["needs_promoter_input"])

    return ClassifyRisksOut(
        company_id=company_id,
        draft_section_id=latest_draft.id,
        version=latest_draft.version,
        items=items,
        flagged_count=flagged_count,
    )