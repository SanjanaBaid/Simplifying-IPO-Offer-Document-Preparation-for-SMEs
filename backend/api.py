import re
from typing import List, Optional

import fitz  # PyMuPDF
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Company,
    ExtractedFinancialLineItem,
    FinancialDocument,
    IntakeSession,
    ScheduleVIField,
)

router = APIRouter()


class IntakeResponseIn(BaseModel):
    field_key: str
    response_text: Optional[str] = None


class IntakeSubmitIn(BaseModel):
    company_id: str
    responses: List[IntakeResponseIn]


class IntakeSubmitOut(BaseModel):
    company_id: str
    saved: int
    skipped: List[str]


class IntakeAnswerOut(BaseModel):
    field_key: str
    response_text: Optional[str] = None


class IntakeGetOut(BaseModel):
    company_id: str
    responses: List[IntakeAnswerOut]


@router.get("/intake", response_model=IntakeGetOut)
def get_intake(company_id: str, db: Session = Depends(get_db)):
    """Returns whatever has already been saved for this company, keyed by
    field_key, so the frontend can pre-fill the guided-intake form on load
    instead of always rendering blank. Without this, POST /intake was
    write-only — reopening a mandate showed every field as INCOMPLETE even
    when the data was sitting in the database."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Unknown company_id: {company_id}")

    rows = (
        db.query(ScheduleVIField.field_key, IntakeSession.response_text)
        .join(IntakeSession, IntakeSession.field_id == ScheduleVIField.id)
        .filter(IntakeSession.company_id == company_id)
        .all()
    )
    return IntakeGetOut(
        company_id=company_id,
        responses=[
            IntakeAnswerOut(field_key=field_key, response_text=response_text)
            for field_key, response_text in rows
        ],
    )


@router.post("/intake", response_model=IntakeSubmitOut)
def submit_intake(payload: IntakeSubmitIn, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == payload.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Unknown company_id: {payload.company_id}")

    saved = 0
    skipped: List[str] = []

    for response in payload.responses:
        field = (
            db.query(ScheduleVIField)
            .filter(ScheduleVIField.field_key == response.field_key)
            .first()
        )
        if not field:
            skipped.append(response.field_key)
            continue

        session_row = (
            db.query(IntakeSession)
            .filter(
                IntakeSession.company_id == company.id,
                IntakeSession.field_id == field.id,
            )
            .first()
        )
        if session_row:
            session_row.response_text = response.response_text
        else:
            session_row = IntakeSession(
                company_id=company.id,
                field_id=field.id,
                response_text=response.response_text,
            )
            db.add(session_row)
        saved += 1

    db.commit()
    return IntakeSubmitOut(company_id=company.id, saved=saved, skipped=skipped)


LINE_ITEM_RE = re.compile(
    r"^(?P<label>[A-Za-z][A-Za-z0-9 &/().,'-]{2,80}?)\s+"
    r"(?P<value>\(?-?[\d,]+(?:\.\d+)?\)?)\s*$"
)


def _parse_number(raw: str) -> Optional[float]:
    cleaned = raw.replace(",", "").strip()
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -value if negative else value


def _extract_line_items(pdf_bytes: bytes):
    """Try native table extraction first, then fall back to regex over text lines."""
    items = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    try:
        for page in doc:
            tables = page.find_tables()
            for table in tables.tables:
                data = table.extract()
                for row in data:
                    if not row or len(row) < 2:
                        continue
                    label = (row[0] or "").strip()
                    if not label:
                        continue
                    for cell in row[1:]:
                        value = _parse_number(str(cell)) if cell else None
                        if value is not None:
                            items.append(
                                {
                                    "label": label,
                                    "value": value,
                                    "period": None,
                                    "raw_row": row,
                                }
                            )
                            break
    except Exception:
        
        pass

    if not items:
        for page in doc:
            for raw_line in page.get_text().splitlines():
                match = LINE_ITEM_RE.match(raw_line.strip())
                if not match:
                    continue
                value = _parse_number(match.group("value"))
                if value is None:
                    continue
                items.append(
                    {
                        "label": match.group("label").strip(),
                        "value": value,
                        "period": None,
                        "raw_row": [raw_line.strip()],
                    }
                )

    doc.close()
    return items


class FinancialLineItemOut(BaseModel):
    label: str
    value: Optional[float] = None
    period: Optional[str] = None


class FinancialsGetOut(BaseModel):
    document_id: Optional[str] = None
    filename: Optional[str] = None
    company_id: str
    line_items: List[FinancialLineItemOut]


@router.get("/financials", response_model=FinancialsGetOut)
def get_financials(company_id: str, db: Session = Depends(get_db)):
    """Returns the most recently uploaded financial document (and its
    extracted line items) for this company, so the frontend can restore the
    extraction results panel on load instead of showing it blank after
    every navigation — the same gap /intake had before it got a GET route."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Unknown company_id: {company_id}")

    document = (
        db.query(FinancialDocument)
        .filter(FinancialDocument.company_id == company_id)
        .order_by(FinancialDocument.uploaded_at.desc())
        .first()
    )
    if not document:
        return FinancialsGetOut(company_id=company_id, line_items=[])

    line_items = (
        db.query(ExtractedFinancialLineItem)
        .filter(ExtractedFinancialLineItem.document_id == document.id)
        .all()
    )
    return FinancialsGetOut(
        document_id=document.id,
        filename=document.filename,
        company_id=company_id,
        line_items=[
            FinancialLineItemOut(label=li.label, value=li.value, period=li.period)
            for li in line_items
        ],
    )


@router.post("/upload-financials")
async def upload_financials(
    company_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Unknown company_id: {company_id}")

    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF financial statements are supported.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        extracted = _extract_line_items(pdf_bytes)
    except Exception as exc:  # malformed PDF, etc.
        raise HTTPException(status_code=422, detail=f"Couldn't parse PDF: {exc}") from exc

    document = FinancialDocument(company_id=company.id, filename=file.filename)
    db.add(document)
    db.flush()  # get document.id before inserting line items

    line_items_out = []
    for item in extracted:
        row = ExtractedFinancialLineItem(
            document_id=document.id,
            label=item["label"],
            value=item["value"],
            period=item["period"],
            raw_row=item["raw_row"],
        )
        db.add(row)
        line_items_out.append(
            {"label": item["label"], "value": item["value"], "period": item["period"]}
        )

    db.commit()

    return {
        "document_id": document.id,
        "filename": document.filename,
        "company_id": company.id,
        "line_items": line_items_out,
    }