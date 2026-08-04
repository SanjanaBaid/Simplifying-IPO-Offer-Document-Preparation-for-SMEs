"""Dev-only convenience script — NOT part of the Phase 1 plan.

Promoter/company creation and auth aren't in scope until a later phase, but
POST /intake and POST /upload-financials both require an existing company_id.
Run this once against a fresh sherpa.db to get a company_id to paste into the
"Company ID" field on the Intake page while testing Step 6.

    python seed_dev.py
"""

import bcrypt

from database import Base, SessionLocal, engine
import models  # noqa: F401 — ensure models are registered before create_all
from models import Company, Promoter

Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    existing = db.query(Company).filter(Company.name == "Dev Test Co").first()
    if existing:
        print(f"Company already exists: {existing.id}")
    else:
        hashed = bcrypt.hashpw(b"devpassword", bcrypt.gensalt()).decode()
        promoter = Promoter(
            full_name="Dev Promoter",
            email="dev-promoter@example.com",
            hashed_password=hashed,
        )
        db.add(promoter)
        db.flush()

        company = Company(promoter_id=promoter.id, name="Dev Test Co", sector="Testing")
        db.add(company)
        db.commit()
        db.refresh(company)
        print(f"Seeded company_id: {company.id}")
finally:
    db.close()
