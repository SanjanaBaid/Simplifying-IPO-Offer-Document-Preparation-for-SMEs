from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr


class PromoterCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    merchant_banking_firm: Optional[str] = None


class PromoterOut(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    merchant_banking_firm: Optional[str] = None

    class Config:
        from_attributes = True


class CompanyCreate(BaseModel):
    name: str
    sector: Optional[str] = None
    proposed_issue_size_cr: Optional[float] = None
    promoter_contact_name: Optional[str] = None


class CompanyOut(BaseModel):
    id: str
    name: str
    sector: Optional[str] = None
    proposed_issue_size_cr: Optional[float] = None
    promoter_contact_name: Optional[str] = None
    completeness_score: int

    class Config:
        from_attributes = True


class ScheduleVIFieldOut(BaseModel):
    id: str
    clause_number: str
    section_name: str
    field_key: str
    plain_language_prompt: str
    field_type: str

    class Config:
        from_attributes = True


class IntakeResponseIn(BaseModel):
    company_id: str
    field_key: str
    response_text: str


class IntakeResponseOut(BaseModel):
    id: str
    field_id: str
    response_text: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class IntakeBulkIn(BaseModel):
    company_id: str
    responses: List[IntakeResponseIn]


class ExtractedLineItemOut(BaseModel):
    id: str
    label: str
    value: Optional[float] = None
    period: Optional[str] = None

    class Config:
        from_attributes = True


class FinancialDocumentOut(BaseModel):
    id: str
    filename: str
    uploaded_at: datetime
    line_items: List[ExtractedLineItemOut] = []

    class Config:
        from_attributes = True


class DraftSectionOut(BaseModel):
    id: str
    section_name: str
    content: Optional[str] = None
    schedule_vi_clause: Optional[str] = None
    version: int

    class Config:
        from_attributes = True