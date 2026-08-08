import uuid
import datetime

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Text,
    ForeignKey,
    DateTime,
    JSON,
    Boolean,
)
from sqlalchemy.orm import relationship

from database import Base


def gen_id():
    return str(uuid.uuid4())


class Promoter(Base):
    __tablename__ = "promoters"

    id = Column(String, primary_key=True, default=gen_id)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    merchant_banking_firm = Column(String, nullable=True)
    
    role = Column(String, default="promoter", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    companies = relationship("Company", back_populates="promoter", foreign_keys="Company.promoter_id")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=gen_id)
    token = Column(String, unique=True, nullable=False, index=True)
    promoter_id = Column(String, ForeignKey("promoters.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    promoter = relationship("Promoter")


class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True, default=gen_id)
    promoter_id = Column(String, ForeignKey("promoters.id"), nullable=False)
    name = Column(String, nullable=False)
    sector = Column(String, nullable=True)
    proposed_issue_size_cr = Column(Float, nullable=True)
    promoter_contact_name = Column(String, nullable=True)
    completeness_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    review_status = Column(String, default="not_reviewed", nullable=False)
    banker_review_comment = Column(Text, nullable=True)
    reviewed_by_banker_id = Column(String, ForeignKey("promoters.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    promoter = relationship("Promoter", back_populates="companies", foreign_keys=[promoter_id])
    intake_sessions = relationship("IntakeSession", back_populates="company")
    financial_documents = relationship("FinancialDocument", back_populates="company")
    draft_sections = relationship("DraftSection", back_populates="company")


class BankerAccess(Base):
    

    __tablename__ = "banker_access"

    id = Column(String, primary_key=True, default=gen_id)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    banker_id = Column(String, ForeignKey("promoters.id"), nullable=False)
    granted_at = Column(DateTime, default=datetime.datetime.utcnow)

    company = relationship("Company")
    banker = relationship("Promoter", foreign_keys=[banker_id])


class ScheduleVIField(Base):
    __tablename__ = "schedule_vi_fields"

    id = Column(String, primary_key=True, default=gen_id)
    clause_number = Column(String, nullable=False)
    section_name = Column(String, nullable=False)
    field_key = Column(String, nullable=False, unique=True)
    plain_language_prompt = Column(Text, nullable=False)
    field_type = Column(String, default="text")

    intake_responses = relationship("IntakeSession", back_populates="field")


class IntakeSession(Base):
    __tablename__ = "intake_sessions"

    id = Column(String, primary_key=True, default=gen_id)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    field_id = Column(String, ForeignKey("schedule_vi_fields.id"), nullable=False)
    response_text = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    company = relationship("Company", back_populates="intake_sessions")
    field = relationship("ScheduleVIField", back_populates="intake_responses")


class FinancialDocument(Base):
    __tablename__ = "financial_documents"

    id = Column(String, primary_key=True, default=gen_id)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    filename = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    company = relationship("Company", back_populates="financial_documents")
    line_items = relationship("ExtractedFinancialLineItem", back_populates="document")


class ExtractedFinancialLineItem(Base):
    __tablename__ = "extracted_financial_line_items"

    id = Column(String, primary_key=True, default=gen_id)
    document_id = Column(String, ForeignKey("financial_documents.id"), nullable=False)
    label = Column(String, nullable=False)
    value = Column(Float, nullable=True)
    period = Column(String, nullable=True)
    raw_row = Column(JSON, nullable=True)

    document = relationship("FinancialDocument", back_populates="line_items")


class DraftSection(Base):
    __tablename__ = "draft_sections"

    id = Column(String, primary_key=True, default=gen_id)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    section_name = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    schedule_vi_clause = Column(String, nullable=True)
    version = Column(Integer, default=1)
   
    is_manual_edit = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    company = relationship("Company", back_populates="draft_sections")


class RiskClassification(Base):


    __tablename__ = "risk_classifications"

    id = Column(String, primary_key=True, default=gen_id)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    draft_section_id = Column(String, ForeignKey("draft_sections.id"), nullable=False)
    version = Column(Integer, default=1)
    items = Column(JSON, nullable=False)
    flagged_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)