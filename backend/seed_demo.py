import bcrypt

from database import Base, SessionLocal, engine
import models
from models import (
    Company,
    DraftSection,
    ExtractedFinancialLineItem,
    FinancialDocument,
    IntakeSession,
    Promoter,
    ScheduleVIField,
)
import seed_schedule_vi_fields

Base.metadata.create_all(bind=engine)

DEMO_COMPANY_NAME = "Aravalli Precision Components Limited"
DEMO_PERIOD = "FY25"

INTAKE_ANSWERS = {
    "company_legal_name": DEMO_COMPANY_NAME,
    "cin": "U29253MH2014PLC256321",
    "registered_office_address": "Plot 14, MIDC Industrial Area, Chakan, Pune, Maharashtra 410501",
    "date_of_incorporation": "2014-03-18",
    "promoter_full_name": "Ashwin Kulkarni",
    "promoter_pan": "ABCDE1234F",
    "nature_of_business": (
        "The Company manufactures precision-machined aluminium castings and forged steel "
        "sub-assemblies for OEM customers in the passenger vehicle and light commercial vehicle "
        "segments, operating on a business-to-business rate-contract model."
    ),
    "key_products_services": (
        "Machined aluminium castings, forged steel sub-assemblies, and aftermarket spare parts "
        "for four OEM customers under annual rate contracts."
    ),
    "manufacturing_locations": "Single manufacturing plant at Chakan, Pune, Maharashtra.",
    "employee_count": "142",
    "issue_size_cr": "31",
    "objects_of_issue": (
        "Funding the purchase of additional CNC machining capacity, repaying a portion of "
        "existing working capital debt, and funding incremental working capital requirements."
    ),
    "proposed_utilization_schedule": (
        "Year 1: CNC machinery purchase and installation. Year 1-2: working capital debt repayment. "
        "Year 2 onward: incremental working capital as order volumes scale."
    ),
    "current_shareholding_pct": "68.4",
    "shareholding_acquisition_history": (
        "Promoter subscribed to 12,00,000 shares at incorporation in 2014 and acquired a further "
        "4,50,000 shares via a rights issue in 2019."
    ),
    "lock_in_eligible_shares": "1250000",
    "related_party_relationship": "promoter-group",
    "related_party_transactions": (
        "FY24 rent of ₹0.42 Cr paid to Ashwin Realty LLP (owned by promoter's spouse); "
        "₹1.10 Cr purchases from Kulkarni Metals Pvt. Ltd. (promoter director)."
    ),
    "operational_risks": (
        "We depend on a single supplier, Bansal Steel Pvt Ltd, for 62% of our raw steel input. "
        "Any disruption to that supplier — such as a supply chain disruption or insolvency — "
        "would materially affect our production."
    ),
    "industry_risks": (
        "The industry is cyclical and our business is subject to general economic conditions "
        "and factors beyond our control."
    ),
    "litigation_disclosure": "None.",
}

RISK_FACTORS_CONTENT = """**Supplier Concentration Risk**
We depend on a single supplier, Bansal Steel Pvt Ltd, for 62% of our raw steel input. Any disruption to this supplier, such as a supply chain disruption or insolvency, would materially affect our production and have a significant impact on our business. This concentration of supply chain risk may adversely affect our ability to meet customer demand and maintain our sales volumes. [Sch. VI, Part A, Cl. 17(i)]

**Industry Cyclicality Risk**
The industry is cyclical and our business is subject to general economic conditions and factors beyond our control. There can be no assurance that demand for our products will remain stable, and any downturn could adversely affect our business, results of operations, and financial condition. [Sch. VI, Part A, Cl. 17(ii)]"""

RISK_FACTORS_CLAUSE = "Sch. VI, Part A, Cl. 17(i), Sch. VI, Part A, Cl. 17(ii)"

CAPITAL_STRUCTURE_CONTENT = """The Company's authorized share capital is ₹5,00,00,000 divided into equity shares of face value ₹10 each. [CAPITAL-STRUCTURE-1]

The Company's paid-up capital stood at ₹4,50,00,000 as of the last financial year, fully subscribed and called up. [CAPITAL-STRUCTURE-2]

Promoter shareholding stood at 68.4% as of the date of this document. The promoter subscribed to shares at incorporation in 2014 and acquired further shares via a rights issue in 2019; 12,50,000 of the promoter's shares are eligible for the minimum promoter contribution lock-in. [Sch. VI, Part A, Cl. 11(ix)]"""

CAPITAL_STRUCTURE_CLAUSE = "CAPITAL-STRUCTURE-1, CAPITAL-STRUCTURE-2, Sch. VI, Part A, Cl. 11(ix)"

FINANCIAL_LINE_ITEMS = [
    {"label": "Authorized Capital", "value": 50000000, "period": DEMO_PERIOD},
    {"label": "Paid-up Capital", "value": 45000000, "period": DEMO_PERIOD},
    {"label": "Promoter Shareholding %", "value": 62.0, "period": DEMO_PERIOD},
    {"label": "Segment Revenue - Machined Aluminium Castings", "value": 4800000, "period": DEMO_PERIOD},
    {"label": "Segment Revenue - Forged Steel Sub-assemblies", "value": 3700000, "period": DEMO_PERIOD},
    {"label": "Segment Revenue - Aftermarket Spare Parts", "value": 1500000, "period": DEMO_PERIOD},
    {"label": "Total Revenue", "value": 10000000, "period": DEMO_PERIOD},
]


def get_or_create_company(db) -> Company:
    existing = db.query(Company).filter(Company.name == DEMO_COMPANY_NAME).first()
    if existing:
        return existing

    hashed = bcrypt.hashpw(b"demopassword", bcrypt.gensalt()).decode()
    promoter = Promoter(
        full_name="Ashwin Kulkarni",
        email="ashwin.kulkarni@aravalli-demo.example",
        hashed_password=hashed,
        merchant_banking_firm="IIT Goa Merchant Advisory",
    )
    db.add(promoter)
    db.flush()

    company = Company(
        promoter_id=promoter.id,
        name=DEMO_COMPANY_NAME,
        sector="Auto Components",
        proposed_issue_size_cr=31.0,
        promoter_contact_name="Ashwin Kulkarni",
    )
    db.add(company)
    db.flush()
    return company


def seed_intake(db, company: Company):
    saved = 0
    for field_key, response_text in INTAKE_ANSWERS.items():
        field = db.query(ScheduleVIField).filter(ScheduleVIField.field_key == field_key).first()
        if not field:
            print(f"  ! skipping '{field_key}' — not found in ScheduleVIField (seed_schedule_vi_fields.py out of sync?)")
            continue
        session_row = (
            db.query(IntakeSession)
            .filter(IntakeSession.company_id == company.id, IntakeSession.field_id == field.id)
            .first()
        )
        if session_row:
            session_row.response_text = response_text
        else:
            db.add(IntakeSession(company_id=company.id, field_id=field.id, response_text=response_text))
        saved += 1
    print(f"  Seeded {saved} intake answers.")


def seed_drafts(db, company: Company):
    for section_name, content, clause in [
        ("Risk Factors", RISK_FACTORS_CONTENT, RISK_FACTORS_CLAUSE),
        ("Capital Structure", CAPITAL_STRUCTURE_CONTENT, CAPITAL_STRUCTURE_CLAUSE),
    ]:
        existing = (
            db.query(DraftSection)
            .filter(DraftSection.company_id == company.id, DraftSection.section_name == section_name)
            .order_by(DraftSection.version.desc())
            .first()
        )
        if existing:
            print(f"  '{section_name}' draft already exists (v{existing.version}) — leaving it as-is.")
            continue
        db.add(
            DraftSection(
                company_id=company.id,
                section_name=section_name,
                content=content,
                schedule_vi_clause=clause,
                version=1,
            )
        )
        print(f"  Seeded '{section_name}' draft (v1).")


def seed_financials(db, company: Company):
    existing = db.query(FinancialDocument).filter(FinancialDocument.company_id == company.id).first()
    if existing:
        print("  Financial document already exists — leaving it as-is.")
        return

    document = FinancialDocument(company_id=company.id, filename="FY25_Provisional_Financials_demo.pdf")
    db.add(document)
    db.flush()

    for item in FINANCIAL_LINE_ITEMS:
        db.add(
            ExtractedFinancialLineItem(
                document_id=document.id,
                label=item["label"],
                value=item["value"],
                period=item["period"],
                raw_row=[item["label"], item["value"]],
            )
        )
    print(f"  Seeded {len(FINANCIAL_LINE_ITEMS)} financial line items.")


def run():
    seed_schedule_vi_fields.run()

    db = SessionLocal()
    try:
        company = get_or_create_company(db)
        print(f"Demo company: {company.name} ({company.id})")
        seed_intake(db, company)
        seed_drafts(db, company)
        seed_financials(db, company)
        db.commit()
        print(f"\nDone. Demo company_id: {company.id}")
    finally:
        db.close()


if __name__ == "__main__":
    run()