from database import Base, SessionLocal, engine
import models  
from models import ScheduleVIField

Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Clause numbering below is grounded in the actual SEBI (ICDR) Regulations,
# 2018, Schedule VI Part A ("Disclosures in offer document/letter of offer"),
# cross-checked against a merchant banker's regulation-wise compliance
# checklist for an SME IPO. Real Part A structure, in order: (1) Cover Pages,
# (4) Offer Document Summary, (5) Risk Factors, (6) Introduction,
# (7) General Information, (8) Capital Structure, (9) Particulars of the
# Issue / Objects of the Issue. This replaces an earlier version of this file
# that invented its own numbering (e.g. treating Risk Factors as clause 17
# and Capital Structure as clause 11) which did not correspond to the real
# regulation at all.
#
# Each field below is tagged [VERIFIED] if its clause_number traces to a
# specific, directly-read Part A item, or [APPROXIMATE] if it's grouped
# under the nearest verified parent item because the primary text available
# for this project didn't itemize that exact sub-point (e.g. promoter PAN
# specifically, or inter-director relationships) — those should be checked
# against the full regulation before relying on them for an actual filing.
FIELDS = [

    # --- Promoter & Company Details -----------------------------------------
    dict(field_key="company_legal_name", clause_number="Sch. VI, Part A, Cl. 7(A)",
         section_name="Promoter & Company Details",
         plain_language_prompt="What is the full legal name of the company, exactly as registered?",
         field_type="text"),  # [VERIFIED] Cl. 7(A): name/address/registration no. of registered office
    dict(field_key="cin", clause_number="Sch. VI, Part A, Cl. 7(A)",
         section_name="Promoter & Company Details",
         plain_language_prompt="What is the company's Corporate Identity Number (CIN)?",
         field_type="text"),  # [VERIFIED] Cl. 7(A)
    dict(field_key="registered_office_address", clause_number="Sch. VI, Part A, Cl. 7(A)",
         section_name="Promoter & Company Details",
         plain_language_prompt="What is the company's registered office address?",
         field_type="textarea"),  # [VERIFIED] Cl. 7(A)
    dict(field_key="date_of_incorporation", clause_number="Sch. VI, Part A, Cl. 1(a)",
         section_name="Promoter & Company Details",
         plain_language_prompt="When was the company incorporated?",
         field_type="date"),  # [VERIFIED] Cl. 1(a): front cover page requires date and place of incorporation
    dict(field_key="promoter_full_name", clause_number="Sch. VI, Part A, Cl. 4(B)",
         section_name="Promoter & Company Details",
         plain_language_prompt="What is the promoter's full name, as it appears on their PAN card?",
         field_type="text"),  # [VERIFIED] Cl. 4(B): "Names of the promoters" in the Offer Document Summary
    dict(field_key="promoter_pan", clause_number="Sch. VI, Part A, Cl. 7(A)",
         section_name="Promoter & Company Details",
         plain_language_prompt="What is the promoter's PAN?",
         field_type="text"),  # [APPROXIMATE] grouped under General Information; PAN isn't separately itemized in the source read
    dict(field_key="promoter_din", clause_number="Sch. VI, Part A, Cl. 7(B)",
         section_name="Promoter & Company Details",
         plain_language_prompt="If the promoter is also a director, what is their DIN? (Leave blank if not applicable.)",
         field_type="text"),  # [VERIFIED] Cl. 7(B): name, designation, address and DIN of each director

    # --- Business & Operations -----------------------------------------------
    dict(field_key="nature_of_business", clause_number="Sch. VI, Part A, Cl. 4(A)",
         section_name="Business & Operations",
         plain_language_prompt="In plain terms, what does the company do and who are its customers?",
         field_type="textarea"),  # [VERIFIED] Cl. 4(A): primary business and industry, in the Offer Document Summary
    dict(field_key="key_products_services", clause_number="Sch. VI, Part A, Cl. 4(A)",
         section_name="Business & Operations",
         plain_language_prompt="What are the company's main products or services?",
         field_type="textarea"),  # [APPROXIMATE] grouped under Cl. 4(A); the full "Our Business" chapter is not itemized in the source read
    dict(field_key="manufacturing_locations", clause_number="Sch. VI, Part A, Cl. 4(A)",
         section_name="Business & Operations",
         plain_language_prompt="Where are the company's manufacturing units or main places of operation?",
         field_type="textarea"),  # [APPROXIMATE] grouped under Cl. 4(A)
    dict(field_key="employee_count", clause_number="Sch. VI, Part A, Cl. 4(A)",
         section_name="Business & Operations",
         plain_language_prompt="How many people does the company currently employ?",
         field_type="number"),  # [APPROXIMATE] grouped under Cl. 4(A)

    # --- Objects of the Issue --------------------------------------------------
    dict(field_key="issue_size_cr", clause_number="Sch. VI, Part A, Cl. 8(A)",
         section_name="Objects of the Issue",
         plain_language_prompt="What is the proposed issue size, in \u20b9 crore?",
         field_type="number"),  # [VERIFIED] Cl. 8(A)(b): size of the present issue, in the Capital Structure table
    dict(field_key="objects_of_issue", clause_number="Reg. 229, Sch. VI Cl. 9(A)",
         section_name="Objects of the Issue",
         plain_language_prompt="What will the company use the raised money for?",
         field_type="textarea"),  # [VERIFIED] Cl. 9(A)(1): objects of the issue
    dict(field_key="proposed_utilization_schedule", clause_number="Reg. 229, Sch. VI Cl. 9(A)",
         section_name="Objects of the Issue",
         plain_language_prompt="Roughly when do you expect to deploy the funds?",
         field_type="textarea"),  # [VERIFIED] Cl. 9(A)(5): utilization schedule disclosures under Objects of the Issue

    # --- Promoter Shareholding History -----------------------------------------
    dict(field_key="current_shareholding_pct", clause_number="Sch. VI, Part A, Cl. 8(B)",
         section_name="Promoter Shareholding History",
         plain_language_prompt="What percentage of the company does the promoter currently hold?",
         field_type="number"),  # [VERIFIED] Cl. 8(B)(h): total shareholding of each promoter, pre/post-issue %
    dict(field_key="shareholding_acquisition_history", clause_number="Sch. VI, Part A, Cl. 8(B)",
         section_name="Promoter Shareholding History",
         plain_language_prompt="How did the promoter acquire these shares — original allotment, purchase, transfer, bonus, etc.?",
         field_type="textarea"),  # [VERIFIED] Cl. 8(B)(k)(i): promoters' contribution — nature of allotment, dates
    dict(field_key="lock_in_eligible_shares", clause_number="Sch. VI, Part A, Cl. 8(B)",
         section_name="Promoter Shareholding History",
         plain_language_prompt="How many of the promoter's shares are eligible for the minimum promoter contribution lock-in?",
         field_type="number"),  # [VERIFIED] Cl. 8(B)(k)(i): lock-in details as part of promoters' contribution table

    # --- Related Party Transactions --------------------------------------------
    dict(field_key="related_party_relationship", clause_number="Sch. VI, Part A, Cl. 4(K)",
         section_name="Related Party Transactions",
         plain_language_prompt="Does the company have any related party relationships to disclose?",
         field_type="select"),  # [VERIFIED] Cl. 4(K): summary of related party transactions, Offer Document Summary
    dict(field_key="related_party_transactions", clause_number="Sch. VI, Part A, Cl. 4(K)",
         section_name="Related Party Transactions",
         plain_language_prompt="Describe any transactions with related parties over the last 3 years. Write \"None\" if not applicable.",
         field_type="textarea"),  # [VERIFIED] Cl. 4(K)

    # --- Risk Factor Inputs ------------------------------------------------------
    dict(field_key="operational_risks", clause_number="Sch. VI, Part A, Cl. 5(B)",
         section_name="Risk Factor Inputs",
         plain_language_prompt="What operational risks worry you most (supply chain, key customers, key personnel, etc.)?",
         field_type="textarea"),  # [VERIFIED] Cl. 5(B): risks internal/specific to the issuer
    dict(field_key="industry_risks", clause_number="Sch. VI, Part A, Cl. 5(B)",
         section_name="Risk Factor Inputs",
         plain_language_prompt="What industry-wide or regulatory risks could affect the business?",
         field_type="textarea"),  # [VERIFIED] Cl. 5(B): risks external to the issuer
    dict(field_key="litigation_disclosure", clause_number="Sch. VI, Part A, Cl. 5(G)",
         section_name="Risk Factor Inputs",
         plain_language_prompt="Is the company, or any promoter/director, currently party to any litigation? Write \"None\" if not applicable.",
         field_type="textarea"),  # [VERIFIED] Cl. 5(G): required risk-factor subject — summary of outstanding litigation

    # --- Management & Key Managerial Personnel -----------------------------------
    dict(field_key="board_composition", clause_number="Sch. VI, Part A, Cl. 7(B)",
         section_name="Management & Key Managerial Personnel",
         plain_language_prompt="Who are the company's directors? List each director's name, designation (e.g. Managing Director, Independent Director), and whether they are a promoter.",
         field_type="textarea"),  # [VERIFIED] Cl. 7(B): name, designation, address and DIN of each director
    dict(field_key="key_managerial_personnel", clause_number="Sch. VI, Part A, Cl. 7(C)",
         section_name="Management & Key Managerial Personnel",
         plain_language_prompt="Who are the company's key managerial personnel (CFO, Company Secretary, and other senior leadership below the board)? Include their designation and relevant experience.",
         field_type="textarea"),  # [VERIFIED, partial] Cl. 7(C) names Company Secretary/legal advisor/bankers; CFO not itemized separately in the source read
    dict(field_key="director_relationships", clause_number="Sch. VI, Part A, Cl. 7(B)",
         section_name="Management & Key Managerial Personnel",
         plain_language_prompt="Are any directors related to each other or to the promoter (spouse, sibling, parent-child, etc.)? Write \"None\" if not applicable.",
         field_type="textarea"),  # [APPROXIMATE] grouped under Cl. 7(B); not itemized as its own sub-clause in the source read
    dict(field_key="management_changes_last_3_years", clause_number="Sch. VI, Part A, Cl. 7(B)",
         section_name="Management & Key Managerial Personnel",
         plain_language_prompt="Have there been any changes to the board of directors or key managerial personnel in the last 3 years? Briefly describe who joined or left, and when.",
         field_type="textarea"),  # [APPROXIMATE] grouped under Cl. 7(B)

    # --- Statutory Approvals & Borrowings ------------------------------------------
    dict(field_key="material_licenses_approvals", clause_number="Sch. VI, Part A, Cl. 5(G)",
         section_name="Statutory Approvals & Borrowings",
         plain_language_prompt="What material licenses, registrations, or approvals does the company currently hold to run its business (e.g. GST registration, factory license, industry-specific permits)?",
         field_type="textarea"),  # [APPROXIMATE] grouped under Cl. 5(G); the source read itemizes pending approvals, not currently-held ones
    dict(field_key="pending_regulatory_approvals", clause_number="Sch. VI, Part A, Cl. 5(G)",
         section_name="Statutory Approvals & Borrowings",
         plain_language_prompt="Are there any licenses or approvals the company has applied for but not yet received? Write \"None\" if not applicable.",
         field_type="textarea"),  # [VERIFIED] Cl. 5(G): required risk-factor subject — statutory clearances/approvals yet to be received
    dict(field_key="outstanding_borrowings", clause_number="Sch. VI, Part A, Cl. 4(F)",
         section_name="Statutory Approvals & Borrowings",
         plain_language_prompt="What are the company's outstanding borrowings — lender name, amount, and security offered (if any)? Write \"None\" if the company has no borrowings.",
         field_type="textarea"),  # [VERIFIED] Cl. 4(F): total borrowings, as part of the restated financial summary table
    dict(field_key="contingent_liabilities", clause_number="Sch. VI, Part A, Cl. 4(J)",
         section_name="Statutory Approvals & Borrowings",
         plain_language_prompt="Does the company have any contingent liabilities — guarantees given on behalf of others, disputed tax demands, pending claims not acknowledged as debt? Write \"None\" if not applicable.",
         field_type="textarea"),  # [VERIFIED] Cl. 4(J): summary table of contingent liabilities
]


def run():
    db = SessionLocal()
    created, skipped = 0, 0
    try:
        for f in FIELDS:
            existing = db.query(ScheduleVIField).filter(ScheduleVIField.field_key == f["field_key"]).first()
            if existing:
                skipped += 1
                continue
            db.add(ScheduleVIField(**f))
            created += 1
        db.commit()
        print(f"Seeded {created} new Schedule VI fields ({skipped} already existed).")
    finally:
        db.close()


if __name__ == "__main__":
    run()