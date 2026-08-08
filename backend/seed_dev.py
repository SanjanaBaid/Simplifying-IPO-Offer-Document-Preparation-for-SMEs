import bcrypt

from database import Base, SessionLocal, engine
import models  # noqa: F401 — ensure models are registered before create_all
from models import Company, Promoter
import seed_schedule_vi_fields

Base.metadata.create_all(bind=engine)

# Without this call, a fresh dev DB has 0 ScheduleVIFields, so /intake (and
# every downstream module that reads from it) renders empty until someone
# separately remembers to run seed_schedule_vi_fields.py by hand.
seed_schedule_vi_fields.run()

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