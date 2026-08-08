import datetime
import secrets

import bcrypt
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session as DbSession

from database import get_db
from models import Company, Promoter, Session as SessionModel

router = APIRouter(tags=["auth"])

SESSION_LIFETIME_DAYS = 7


class SignupIn(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    merchant_banking_firm: str | None = None
    role: str = "promoter"  


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class PromoterOut(BaseModel):
    id: str
    full_name: str
    email: str
    merchant_banking_firm: str | None = None
    role: str = "promoter"


class AuthOut(BaseModel):
    token: str
    promoter: PromoterOut


def _hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def _verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode(), hashed.encode())
    except ValueError:
        return False


def _promoter_out(p: Promoter) -> PromoterOut:
   
    return PromoterOut(
        id=p.id,
        full_name=p.full_name,
        email=p.email,
        merchant_banking_firm=p.merchant_banking_firm,
        role=p.role,
    )


def _issue_session(promoter: Promoter, db: DbSession) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=SESSION_LIFETIME_DAYS)
    db.add(SessionModel(token=token, promoter_id=promoter.id, expires_at=expires_at))
    db.commit()
    return token


def get_current_promoter(
    authorization: str | None = Header(default=None),
    db: DbSession = Depends(get_db),
) -> Promoter:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")
    token = authorization.split(" ", 1)[1].strip()

    session = db.query(SessionModel).filter(SessionModel.token == token).first()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session. Please sign in again.")
    if session.expires_at < datetime.datetime.utcnow():
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")

    promoter = db.query(Promoter).filter(Promoter.id == session.promoter_id).first()
    if not promoter:
        raise HTTPException(status_code=401, detail="Account no longer exists.")
    return promoter


@router.post("/auth/signup", response_model=AuthOut)
def signup(payload: SignupIn, db: DbSession = Depends(get_db)):
    existing = db.query(Promoter).filter(Promoter.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    role = payload.role if payload.role in ("promoter", "banker") else "promoter"
    promoter = Promoter(
        full_name=payload.full_name.strip(),
        email=payload.email.lower(),
        hashed_password=_hash_password(payload.password),
        merchant_banking_firm=payload.merchant_banking_firm,
        role=role,
    )
    db.add(promoter)
    db.commit()
    db.refresh(promoter)

    token = _issue_session(promoter, db)
    return AuthOut(token=token, promoter=_promoter_out(promoter))


@router.post("/auth/login", response_model=AuthOut)
def login(payload: LoginIn, db: DbSession = Depends(get_db)):
    promoter = db.query(Promoter).filter(Promoter.email == payload.email.lower()).first()
    if not promoter or not _verify_password(payload.password, promoter.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = _issue_session(promoter, db)
    return AuthOut(token=token, promoter=_promoter_out(promoter))


@router.post("/auth/logout")
def logout(authorization: str | None = Header(default=None), db: DbSession = Depends(get_db)):
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        session = db.query(SessionModel).filter(SessionModel.token == token).first()
        if session:
            db.delete(session)
            db.commit()
    return {"status": "ok"}


@router.get("/auth/me", response_model=PromoterOut)
def me(current: Promoter = Depends(get_current_promoter)):
    return _promoter_out(current)


class MandateIn(BaseModel):
    name: str
    sector: str | None = None
    proposed_issue_size_cr: float | None = None
    promoter_contact_name: str | None = None


class MandateOut(BaseModel):
    id: str
    name: str
    sector: str | None = None
    proposed_issue_size_cr: float | None = None
    promoter_contact_name: str | None = None
    completeness_score: int = 0


def _mandate_out(c: Company) -> MandateOut:
    return MandateOut(
        id=c.id,
        name=c.name,
        sector=c.sector,
        proposed_issue_size_cr=c.proposed_issue_size_cr,
        promoter_contact_name=c.promoter_contact_name,
        completeness_score=c.completeness_score,
    )


@router.get("/companies", response_model=list[MandateOut])
def list_mandates(current: Promoter = Depends(get_current_promoter), db: DbSession = Depends(get_db)):
   
    from handoff import compute_scorecard

    companies = (
        db.query(Company)
        .filter(Company.promoter_id == current.id)
        .order_by(Company.created_at.desc())
        .all()
    )

   
    for c in companies:
        try:
            result = compute_scorecard(db, c)
            c.completeness_score = result["total_score"]
        except Exception:
           
            pass
    db.commit()

    return [_mandate_out(c) for c in companies]


@router.post("/companies", response_model=MandateOut)
def create_mandate(
    payload: MandateIn,
    current: Promoter = Depends(get_current_promoter),
    db: DbSession = Depends(get_db),
):
    company = Company(
        promoter_id=current.id,
        name=payload.name.strip(),
        sector=payload.sector,
        proposed_issue_size_cr=payload.proposed_issue_size_cr,
        promoter_contact_name=payload.promoter_contact_name,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return _mandate_out(company)