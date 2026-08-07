"""
Drafting Engine API (Phase 2, Step 7).

Retrieves relevant Schedule VI / ICDR clauses from the ChromaDB knowledge base
built by ingest.py, combines them with a company's intake answers (and, for
Capital Structure, its extracted financial line items), and drafts offer
document sections via an LLM. Each generated section is saved as a new
DraftSection version, tagged with the Schedule VI clause(s) it was grounded in.

Endpoints:
    GET  /drafting/clauses    — raw clause retrieval for a section (debugging /
                                 letting the UI preview what will be cited)
    POST /drafting/generate   — full generate-and-save pipeline for a section

Wire into main.py:
    from drafting import router as drafting_router
    app.include_router(drafting_router)

Requires the knowledge base to already be ingested (see ingest.py) and, to
actually call the LLM, a GROQ_API_KEY in the environment (free tier, no card
required — https://console.groq.com/keys). Without a key set,
/drafting/generate still runs end-to-end but returns a clearly-marked stub
draft, so Step 8 (Drafting UI) can be built and tested against this endpoint
without needing real credentials.
"""

import os
from typing import Dict, List, Literal, Optional

import chromadb
from chromadb.utils import embedding_functions
from fastapi import APIRouter, Depends, HTTPException
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

router = APIRouter(prefix="/drafting", tags=["drafting"])

# ---------------------------------------------------------------------------
# ChromaDB access — same persist dir / collection name as ingest.py
# ---------------------------------------------------------------------------

CHROMA_PERSIST_DIR = "./chroma_store"
COLLECTION_NAME = "sebi_icdr_schedule_vi"

_chroma_client = None
_collection = None


def _get_collection():
    """Lazily open the persistent ChromaDB collection ingest.py wrote to."""
    global _chroma_client, _collection
    if _collection is not None:
        return _collection

    _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    embed_fn = embedding_functions.DefaultEmbeddingFunction()
    try:
        _collection = _chroma_client.get_collection(name=COLLECTION_NAME, embedding_function=embed_fn)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Knowledge base collection '{COLLECTION_NAME}' isn't available yet. "
                "Run `python ingest.py --source <regulation file>` first."
            ),
        ) from exc
    return _collection


def retrieve_clauses(query: str, top_k: int = 5) -> List[Dict]:
    """Query ChromaDB for the clauses most relevant to `query`."""
    collection = _get_collection()
    results = collection.query(query_texts=[query], n_results=top_k)

    clauses: List[Dict] = []
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else [None] * len(ids)

    for chunk_id, text, meta, distance in zip(ids, documents, metadatas, distances):
        clauses.append(
            {
                "id": chunk_id,
                "clause_number": (meta or {}).get("clause_number", "Unknown"),
                "source": (meta or {}).get("source", "Unknown"),
                "text": text,
                "distance": distance,
            }
        )
    return clauses


# ---------------------------------------------------------------------------
# Section registry — maps a section request to its retrieval query, the
# intake fields it draws on, and (for Capital Structure) which extracted
# financial line items are relevant.
# ---------------------------------------------------------------------------

SectionKey = Literal[
    "general_information",
    "business_overview",
    "objects_of_issue",
    "risk_factors",
    "capital_structure",
]

SECTION_CONFIG: Dict[str, Dict] = {
    "general_information": {
        "display_name": "General Information",
        "retrieval_query": (
            "general information company particulars registered office CIN "
            "incorporation promoter details SME issuer disclosure"
        ),
        "intake_field_keys": [
            "company_legal_name",
            "cin",
            "registered_office_address",
            "date_of_incorporation",
            "promoter_full_name",
            "promoter_pan",
            "promoter_din",
        ],
        "financial_line_labels": [],
    },
    "business_overview": {
        "display_name": "Business Overview",
        "retrieval_query": (
            "business overview nature of business products services "
            "manufacturing operations employees SME issuer disclosure"
        ),
        "intake_field_keys": [
            "nature_of_business",
            "key_products_services",
            "manufacturing_locations",
            "employee_count",
        ],
        "financial_line_labels": [],
    },
    "objects_of_issue": {
        "display_name": "Objects of the Issue",
        "retrieval_query": (
            "objects of the issue use of proceeds utilization schedule "
            "issue size SME IPO fund requirement"
        ),
        "intake_field_keys": ["issue_size_cr", "objects_of_issue", "proposed_utilization_schedule"],
        "financial_line_labels": [],
    },
    "risk_factors": {
        "display_name": "Risk Factors",
        "retrieval_query": (
            "risk factors disclosure requirements internal external risks "
            "SME issuer material risk ranking related party transactions"
        ),
        "intake_field_keys": [
            "operational_risks",
            "industry_risks",
            "litigation_disclosure",
            "related_party_relationship",
            "related_party_transactions",
        ],
        "financial_line_labels": [],
    },
    "capital_structure": {
        "display_name": "Capital Structure",
        "retrieval_query": (
            "capital structure authorized capital issued paid-up capital "
            "share capital history promoter shareholding lock-in"
        ),
        "intake_field_keys": [
            "current_shareholding_pct",
            "shareholding_acquisition_history",
            "lock_in_eligible_shares",
        ],
        "financial_line_labels": [
            "authorized capital",
            "authorised capital",
            "paid-up capital",
            "paid up capital",
            "issued capital",
            "share capital",
            "equity share capital",
        ],
    },
}


def _gather_intake_answers(db: Session, company_id: str, field_keys: List[str]) -> Dict[str, Optional[str]]:
    """Return {field_key: response_text} for the given fields, None if unanswered."""
    if not field_keys:
        return {}

    rows = (
        db.query(ScheduleVIField.field_key, IntakeSession.response_text)
        .join(IntakeSession, IntakeSession.field_id == ScheduleVIField.id)
        .filter(IntakeSession.company_id == company_id, ScheduleVIField.field_key.in_(field_keys))
        .all()
    )
    answers = {field_key: response_text for field_key, response_text in rows}
    return {key: answers.get(key) for key in field_keys}


def _gather_financial_line_items(db: Session, company_id: str, labels: List[str]) -> List[Dict]:
    """Return extracted line items whose label matches one of `labels` (case-insensitive substring)."""
    if not labels:
        return []

    rows = (
        db.query(ExtractedFinancialLineItem)
        .join(FinancialDocument, FinancialDocument.id == ExtractedFinancialLineItem.document_id)
        .filter(FinancialDocument.company_id == company_id)
        .all()
    )
    lowered_labels = [label.lower() for label in labels]
    matches = []
    for row in rows:
        row_label = (row.label or "").lower()
        if any(target in row_label for target in lowered_labels):
            matches.append({"label": row.label, "value": row.value, "period": row.period})
    return matches


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_COMMON_SYSTEM_PROMPT = """You are a drafting assistant for SME IPO offer documents, working under \
SEBI ICDR Regulations (Schedule VI / SME Chapter IX). You draft offer-document sections that:
- Are grounded ONLY in the regulatory clauses provided and the promoter's own intake answers.
- Never invent facts, figures, or disclosures the promoter did not provide.
- Cite the Schedule VI clause number inline in square brackets, e.g. [Sch. VI, Part A, Cl. 17(i)], \
immediately after each disclosure drawn from that clause.
- Flag any promoter answer that is missing, vague, or boilerplate rather than filling it in yourself.
- Use plain, factual, formal offer-document language — no marketing language.
"""


def _format_clauses(clauses: List[Dict]) -> str:
    if not clauses:
        return "(No matching clauses were retrieved — draft only from intake answers, and note the gap.)"
    return "\n\n".join(
        f"[{c['clause_number']}] (source: {c['source']})\n{c['text']}" for c in clauses
    )


def _format_intake(answers: Dict[str, Optional[str]]) -> str:
    lines = []
    for field_key, response_text in answers.items():
        value = response_text.strip() if response_text and response_text.strip() else "(not provided)"
        lines.append(f"- {field_key}: {value}")
    return "\n".join(lines) if lines else "(No intake answers on file.)"


def build_general_information_prompt(clauses: List[Dict], intake_answers: Dict[str, Optional[str]], company_name: str) -> str:
    return f"""Draft the "General Information" section of the offer document for {company_name}.

RELEVANT SCHEDULE VI / ICDR CLAUSES:
{_format_clauses(clauses)}

COMPANY & PROMOTER PARTICULARS (from intake):
{_format_intake(intake_answers)}

Instructions:
1. State the company's full legal name, CIN, registered office address, and date of incorporation.
2. Identify the promoter(s) by name, PAN, and DIN (if a director).
3. Cite the governing clause number in square brackets after each disclosure.
4. If any particular is "(not provided)", write "[NEEDS PROMOTER INPUT: <what's missing>]" instead of \
guessing — never invent a CIN, PAN, DIN, or address.
"""


def build_business_overview_prompt(clauses: List[Dict], intake_answers: Dict[str, Optional[str]], company_name: str) -> str:
    return f"""Draft the "Business Overview" section of the offer document for {company_name}.

RELEVANT SCHEDULE VI / ICDR CLAUSES:
{_format_clauses(clauses)}

BUSINESS & OPERATIONS PARTICULARS (from intake):
{_format_intake(intake_answers)}

Instructions:
1. Describe the nature of the company's business and its key products or services in plain, factual terms.
2. State where the company manufactures or operates from, and its current employee count.
3. Cite the governing clause number in square brackets after each disclosure.
4. If an intake answer is "(not provided)" or too vague to disclose accurately, write \
"[NEEDS PROMOTER INPUT: <what's missing>]" rather than filling it in yourself.
"""


def build_objects_of_issue_prompt(clauses: List[Dict], intake_answers: Dict[str, Optional[str]], company_name: str) -> str:
    return f"""Draft the "Objects of the Issue" section of the offer document for {company_name}.

RELEVANT SCHEDULE VI / ICDR CLAUSES:
{_format_clauses(clauses)}

PROPOSED ISSUE PARTICULARS (from intake):
{_format_intake(intake_answers)}

Instructions:
1. State the proposed issue size in ₹ crore.
2. Explain what the company intends to use the raised funds for (objects of the issue).
3. Set out the proposed utilization schedule if one was provided.
4. Cite the governing clause/regulation number in square brackets after each disclosure.
5. If an intake answer is "(not provided)", write "[NEEDS PROMOTER INPUT: <what's missing>]" instead of \
guessing at figures or a schedule.
"""


def build_risk_factors_prompt(clauses: List[Dict], intake_answers: Dict[str, Optional[str]], company_name: str) -> str:
    return f"""Draft the "Risk Factors" section of the offer document for {company_name}.

RELEVANT SCHEDULE VI / ICDR CLAUSES:
{_format_clauses(clauses)}

PROMOTER-REPORTED RISKS (from intake):
{_format_intake(intake_answers)}

Instructions:
1. Produce one risk factor per distinct risk raised by the promoter, each as its own paragraph with a \
short bolded heading. This includes any related-party relationships or transactions reported above — \
draft a "Related Party Risk" factor from those answers the same way you would any other risk.
2. Quantify materiality where the promoter gave numbers; otherwise state the risk specifically to this \
company's business rather than in generic industry terms.
3. Cite the governing clause number in square brackets at the end of each risk factor.
4. If an intake answer is "(not provided)" or clearly generic, still draft a placeholder risk factor but \
prefix it with "[NEEDS PROMOTER INPUT]" so it can be routed back for review.
"""


def build_capital_structure_prompt(
    clauses: List[Dict],
    intake_answers: Dict[str, Optional[str]],
    financial_line_items: List[Dict],
    company_name: str,
) -> str:
    financial_lines = (
        "\n".join(f"- {item['label']}: {item['value']} ({item['period'] or 'period unspecified'})" for item in financial_line_items)
        if financial_line_items
        else "(No authorized/paid-up capital line items found in uploaded financials yet.)"
    )

    return f"""Draft the "Capital Structure" section of the offer document for {company_name}.

RELEVANT SCHEDULE VI / ICDR CLAUSES:
{_format_clauses(clauses)}

EXTRACTED AUTHORIZED / PAID-UP CAPITAL & SHARE CAPITAL LINE ITEMS (from uploaded financials):
{financial_lines}

PROMOTER SHAREHOLDING & LOCK-IN (from intake):
{_format_intake(intake_answers)}

Instructions:
1. State the authorized share capital and issued/subscribed/paid-up capital using the extracted figures. \
If a figure is missing, write "[NEEDS PROMOTER INPUT: <what's missing>]" instead of guessing.
2. Summarize the promoter's shareholding history and how it was acquired.
3. State how many shares are eligible for the minimum promoter contribution lock-in.
4. Cite the governing clause number in square brackets after each disclosure.
"""


SECTION_PROMPT_BUILDERS = {
    "general_information": build_general_information_prompt,
    "business_overview": build_business_overview_prompt,
    "objects_of_issue": build_objects_of_issue_prompt,
    "risk_factors": build_risk_factors_prompt,
    "capital_structure": build_capital_structure_prompt,
}


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

# Groq's free tier hosts fast, hosted open-weight models (Llama, etc.) behind
# an OpenAI-compatible chat completions API — no card required to get a key.
DRAFTING_LLM_MODEL = os.getenv("DRAFTING_LLM_MODEL", "llama-3.3-70b-versatile")


def call_llm(user_prompt: str) -> str:
    """Call the configured LLM. Falls back to a labeled stub if no API key is set,
    so the endpoint stays testable in /docs without credentials."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return (
            "[STUB DRAFT — set GROQ_API_KEY to generate a real draft]\n\n"
            + user_prompt
        )

    from groq import Groq  # imported lazily so the package is only required when a key is set

    client = Groq(api_key=api_key, timeout=20.0)
    response = client.chat.completions.create(
        model=DRAFTING_LLM_MODEL,
        max_tokens=1500,
        messages=[
            {"role": "system", "content": _COMMON_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ClauseOut(BaseModel):
    clause_number: str
    source: str
    text: str
    distance: Optional[float] = None


class ClausesQueryOut(BaseModel):
    section: str
    query: str
    clauses: List[ClauseOut]


class DraftGenerateIn(BaseModel):
    company_id: str
    section: SectionKey
    top_k: int = 5


class DraftGenerateOut(BaseModel):
    id: str
    company_id: str
    section_key: str
    section_name: str
    version: int
    content: str
    schedule_vi_clause: Optional[str] = None
    retrieved_clauses: List[ClauseOut]
    missing_intake_fields: List[str]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/clauses", response_model=ClausesQueryOut)
def get_clauses_for_section(section: SectionKey, query: Optional[str] = None, top_k: int = 5):
    """Preview which Schedule VI clauses would be retrieved for a section (or a custom query)."""
    config = SECTION_CONFIG[section]
    effective_query = query or config["retrieval_query"]
    clauses = retrieve_clauses(effective_query, top_k=top_k)
    return ClausesQueryOut(section=section, query=effective_query, clauses=clauses)


@router.get("/sections", response_model=List[DraftGenerateOut])
def list_latest_sections(
    company_id: str,
    current: Promoter = Depends(get_current_promoter),
    db: Session = Depends(get_db),
):
    """Return the latest saved version of every drafted section for a company,
    without calling the LLM or bumping the version — used to restore the
    Drafting page's state on mount instead of showing it blank until the
    user clicks 'Generate' again."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Unknown company_id: {company_id}")
    if company.promoter_id != current.id:
        raise HTTPException(status_code=403, detail="You don't have access to this company.")

    out: List[DraftGenerateOut] = []
    for section_key, config in SECTION_CONFIG.items():
        latest = (
            db.query(DraftSection)
            .filter(
                DraftSection.company_id == company.id,
                DraftSection.section_name == config["display_name"],
            )
            .order_by(DraftSection.version.desc())
            .first()
        )
        if not latest:
            continue

        intake_answers = _gather_intake_answers(db, company.id, config["intake_field_keys"])
        missing_fields = [key for key, value in intake_answers.items() if not value or not value.strip()]

        out.append(
            DraftGenerateOut(
                id=latest.id,
                company_id=company.id,
                section_key=section_key,
                section_name=latest.section_name,
                version=latest.version,
                content=latest.content,
                schedule_vi_clause=latest.schedule_vi_clause,
                retrieved_clauses=[],
                missing_intake_fields=missing_fields,
            )
        )
    return out


@router.post("/generate", response_model=DraftGenerateOut)
def generate_draft_section(
    payload: DraftGenerateIn,
    current: Promoter = Depends(get_current_promoter),
    db: Session = Depends(get_db),
):
    """Retrieve clauses + intake answers for a section, draft it via the LLM, and save a new version."""
    company = db.query(Company).filter(Company.id == payload.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Unknown company_id: {payload.company_id}")
    if company.promoter_id != current.id:
        raise HTTPException(status_code=403, detail="You don't have access to this company.")

    config = SECTION_CONFIG[payload.section]

    intake_answers = _gather_intake_answers(db, company.id, config["intake_field_keys"])
    missing_fields = [key for key, value in intake_answers.items() if not value or not value.strip()]

    clauses = retrieve_clauses(config["retrieval_query"], top_k=payload.top_k)

    builder = SECTION_PROMPT_BUILDERS[payload.section]
    if config["financial_line_labels"]:
        financial_items = _gather_financial_line_items(db, company.id, config["financial_line_labels"])
        prompt = builder(clauses, intake_answers, financial_items, company.name)
    else:
        prompt = builder(clauses, intake_answers, company.name)

    draft_text = call_llm(prompt)

    clause_citation = ", ".join(sorted({c["clause_number"] for c in clauses})) or None

    latest_version = (
        db.query(DraftSection)
        .filter(DraftSection.company_id == company.id, DraftSection.section_name == config["display_name"])
        .order_by(DraftSection.version.desc())
        .first()
    )
    next_version = (latest_version.version + 1) if latest_version else 1

    draft_row = DraftSection(
        company_id=company.id,
        section_name=config["display_name"],
        content=draft_text,
        schedule_vi_clause=clause_citation,
        version=next_version,
    )
    db.add(draft_row)
    db.commit()
    db.refresh(draft_row)

    return DraftGenerateOut(
        id=draft_row.id,
        company_id=company.id,
        section_key=payload.section,
        section_name=draft_row.section_name,
        version=draft_row.version,
        content=draft_row.content,
        schedule_vi_clause=draft_row.schedule_vi_clause,
        retrieved_clauses=clauses,
        missing_intake_fields=missing_fields,
    )