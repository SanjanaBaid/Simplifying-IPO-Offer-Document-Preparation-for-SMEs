import re
from typing import List, Optional

import fitz 
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_promoter
from database import get_db
from models import (
    Company,
    ExtractedFinancialLineItem,
    FinancialDocument,
    IntakeSession,
    Promoter,
    ScheduleVIField,
)

router = APIRouter()


def _get_owned_company(company_id: str, current: Promoter, db: Session) -> Company:
    
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Unknown company_id: {company_id}")
    if company.promoter_id != current.id:
        raise HTTPException(status_code=403, detail="You don't have access to this company.")
    return company


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
def get_intake(
    company_id: str,
    current: Promoter = Depends(get_current_promoter),
    db: Session = Depends(get_db),
):
    
    _get_owned_company(company_id, current, db)

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
def submit_intake(
    payload: IntakeSubmitIn,
    current: Promoter = Depends(get_current_promoter),
    db: Session = Depends(get_db),
):
    company = _get_owned_company(payload.company_id, current, db)

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


_PERIOD_PATTERNS = [
    re.compile(r"\bFY\s?(\d{2})\s?[-–]\s?(\d{2})\b", re.IGNORECASE), 
    re.compile(r"\bFY\s?'?(\d{2,4})\b", re.IGNORECASE),  
    re.compile(r"\bF\.?Y\.?\s?(\d{4})\s?[-–]\s?(\d{2,4})\b", re.IGNORECASE),
    re.compile(
        r"year ended\s+(?:\d{1,2}(?:st|nd|rd|th)?\s+)?March,?\s+(\d{4})", re.IGNORECASE
    ),  
    re.compile(r"\b(\d{4})\s?[-–]\s?(\d{2})\b"),  
]


def _detect_period(page_text: str) -> Optional[str]:
    
    for pattern in _PERIOD_PATTERNS:
        match = pattern.search(page_text)
        if not match:
            continue
        groups = match.groups()
        if len(groups) == 2 and groups[1]:
            return f"FY{groups[0]}-{groups[1]}"
        return f"FY{groups[0]}"
    return None


def _extract_line_items(pdf_bytes: bytes):
    
    items = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    try:
        for page in doc:
            page_period = _detect_period(page.get_text())
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
                                    "period": page_period,
                                    "raw_row": row,
                                }
                            )
                            break
    except Exception:
        
        pass

    if not items:
        for page in doc:
            page_period = _detect_period(page.get_text())
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
                        "period": page_period,
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
def get_financials(
    company_id: str,
    current: Promoter = Depends(get_current_promoter),
    db: Session = Depends(get_db),
):
    
    _get_owned_company(company_id, current, db)

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
    current: Promoter = Depends(get_current_promoter),
    db: Session = Depends(get_db),
):
    company = _get_owned_company(company_id, current, db)

    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF financial statements are supported.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        extracted = _extract_line_items(pdf_bytes)
    except Exception as exc:  # malformed PDF, etc.
        raise HTTPException(status_code=422, detail=f"Couldn't parse PDF: {exc}") from exc

    
    old_documents = db.query(FinancialDocument).filter(FinancialDocument.company_id == company.id).all()
    for old_doc in old_documents:
        db.query(ExtractedFinancialLineItem).filter(
            ExtractedFinancialLineItem.document_id == old_doc.id
        ).delete(synchronize_session=False)
        db.delete(old_doc)

    document = FinancialDocument(company_id=company.id, filename=file.filename)
    db.add(document)
    db.flush()  

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

    response = {
        "document_id": document.id,
        "filename": document.filename,
        "company_id": company.id,
        "line_items": line_items_out,
    }
    if not line_items_out:
        
        response["warning"] = (
            "No line items could be extracted from this PDF. This tool reads native, "
            "text-layer PDFs — if this file is a scanned document or an image-based "
            "export, its text isn't machine-readable and won't extract. Try a PDF "
            "exported directly from accounting software rather than a scan."
        )
    return response