import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_promoter
from database import get_db
from models import BankerAccess, Company, DraftSection, Promoter

router = APIRouter(tags=["banker"])


def _require_banker(current: Promoter) -> Promoter:
    if current.role != "banker":
        raise HTTPException(status_code=403, detail="This endpoint is for merchant banker accounts only.")
    return current


def _require_promoter(current: Promoter) -> Promoter:
    if current.role != "promoter":
        raise HTTPException(status_code=403, detail="Only promoter accounts can share a mandate with a banker.")
    return current


def _get_accessible_company(company_id: str, banker: Promoter, db: Session) -> Company:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Unknown company_id: {company_id}")
    access = (
        db.query(BankerAccess)
        .filter(BankerAccess.company_id == company_id, BankerAccess.banker_id == banker.id)
        .first()
    )
    if not access:
        raise HTTPException(status_code=403, detail="This mandate hasn't been shared with your account.")
    return company


class ShareWithBankerIn(BaseModel):
    banker_email: str


class ShareWithBankerOut(BaseModel):
    company_id: str
    banker_email: str
    already_shared: bool


@router.post("/companies/{company_id}/share-with-banker", response_model=ShareWithBankerOut)
def share_with_banker(
    company_id: str,
    payload: ShareWithBankerIn,
    current: Promoter = Depends(get_current_promoter),
    db: Session = Depends(get_db),
):
    _require_promoter(current)

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Unknown company_id: {company_id}")
    if company.promoter_id != current.id:
        raise HTTPException(status_code=403, detail="You don't have access to this company.")

    banker = (
        db.query(Promoter)
        .filter(Promoter.email == payload.banker_email.lower(), Promoter.role == "banker")
        .first()
    )
    if not banker:
        raise HTTPException(
            status_code=404,
            detail="No merchant banker account found with that email. They need to sign up with the 'Merchant Banker' role first.",
        )

    existing = (
        db.query(BankerAccess)
        .filter(BankerAccess.company_id == company_id, BankerAccess.banker_id == banker.id)
        .first()
    )
    if existing:
        return ShareWithBankerOut(company_id=company_id, banker_email=banker.email, already_shared=True)

    db.add(BankerAccess(company_id=company_id, banker_id=banker.id))
    db.commit()
    return ShareWithBankerOut(company_id=company_id, banker_email=banker.email, already_shared=False)


class BankerMandateOut(BaseModel):
    id: str
    name: str
    sector: Optional[str] = None
    proposed_issue_size_cr: Optional[float] = None
    promoter_contact_name: Optional[str] = None
    completeness_score: int = 0
    review_status: str = "not_reviewed"


def _banker_mandate_out(c: Company) -> BankerMandateOut:
    return BankerMandateOut(
        id=c.id,
        name=c.name,
        sector=c.sector,
        proposed_issue_size_cr=c.proposed_issue_size_cr,
        promoter_contact_name=c.promoter_contact_name,
        completeness_score=c.completeness_score,
        review_status=c.review_status,
    )


@router.get("/banker/mandates", response_model=List[BankerMandateOut])
def list_banker_mandates(current: Promoter = Depends(get_current_promoter), db: Session = Depends(get_db)):
    _require_banker(current)

    from handoff import compute_scorecard  # lazy import — see auth.py's list_mandates for why

    grants = db.query(BankerAccess).filter(BankerAccess.banker_id == current.id).all()
    companies = []
    for grant in grants:
        company = db.query(Company).filter(Company.id == grant.company_id).first()
        if not company:
            continue
        try:
            result = compute_scorecard(db, company)
            company.completeness_score = result["total_score"]
        except Exception:
            pass
        companies.append(company)
    db.commit()

    return [_banker_mandate_out(c) for c in companies]


class BankerDraftSectionOut(BaseModel):
    section_name: str
    version: int
    content: Optional[str] = None
    schedule_vi_clause: Optional[str] = None


class BankerMandateDetailOut(BaseModel):
    company: BankerMandateOut
    modules: List[dict]
    gap_list: List[dict]
    draft_sections: List[BankerDraftSectionOut]


@router.get("/banker/mandates/{company_id}", response_model=BankerMandateDetailOut)
def get_banker_mandate_detail(
    company_id: str,
    current: Promoter = Depends(get_current_promoter),
    db: Session = Depends(get_db),
):
    _require_banker(current)
    company = _get_accessible_company(company_id, current, db)

    from handoff import compute_scorecard

    result = compute_scorecard(db, company)
    company.completeness_score = result["total_score"]
    db.commit()

    draft_sections = [
        BankerDraftSectionOut(
            section_name=d.section_name,
            version=d.version,
            content=d.content,
            schedule_vi_clause=d.schedule_vi_clause,
        )
        for d in result["latest_drafts"].values()
    ]

    return BankerMandateDetailOut(
        company=_banker_mandate_out(company),
        modules=result["modules"],
        gap_list=result["gap_list"],
        draft_sections=draft_sections,
    )


class BankerReviewIn(BaseModel):
    status: str  
    comment: Optional[str] = None


class BankerReviewOut(BaseModel):
    company_id: str
    review_status: str
    banker_review_comment: Optional[str] = None
    reviewed_at: Optional[str] = None


ALLOWED_REVIEW_STATUSES = {"approved", "changes_requested", "reviewed"}


@router.post("/banker/mandates/{company_id}/review", response_model=BankerReviewOut)
def submit_banker_review(
    company_id: str,
    payload: BankerReviewIn,
    current: Promoter = Depends(get_current_promoter),
    db: Session = Depends(get_db),
):
    _require_banker(current)
    company = _get_accessible_company(company_id, current, db)

    if payload.status not in ALLOWED_REVIEW_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of {sorted(ALLOWED_REVIEW_STATUSES)}",
        )

    company.review_status = payload.status
    company.banker_review_comment = payload.comment
    company.reviewed_by_banker_id = current.id
    company.reviewed_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(company)

    return BankerReviewOut(
        company_id=company.id,
        review_status=company.review_status,
        banker_review_comment=company.banker_review_comment,
        reviewed_at=company.reviewed_at.isoformat() if company.reviewed_at else None,
    )
