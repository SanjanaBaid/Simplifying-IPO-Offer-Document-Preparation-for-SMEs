// Schedule VI field catalogue — mirrors backend/models.py::ScheduleVIField 1:1.
//
// Each entry here corresponds to one row Person A's ScheduleVIField table will hold:
//   clause_number, section_name, field_key, plain_language_prompt, field_type
//
// `validate` is a small client-side stand-in for the Pydantic validators Person A
// will define server-side for POST /intake in Step 5 (required-ness, length bounds,
// numeric ranges, and regex formats). Keeping the shapes identical means the payload
// this form produces should pass those validators unchanged once Step 5 lands.

const PAN_RE = /^[A-Z]{5}[0-9]{4}[A-Z]$/;
const CIN_RE = /^[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$/;
const DIN_RE = /^[0-9]{8}$/;

const required = (label) => (v) => {
  if (v === undefined || v === null || String(v).trim() === "") {
    return `${label} is required.`;
  }
  return null;
};

const minLength = (n) => (v) =>
  v && String(v).trim().length < n ? `Please provide at least ${n} characters.` : null;

const pattern = (re, msg) => (v) => (v && !re.test(String(v).trim()) ? msg : null);

const numberRange = (min, max) => (v) => {
  if (v === "" || v === undefined || v === null) return null;
  const n = Number(v);
  if (Number.isNaN(n)) return "Must be a number.";
  if (min !== undefined && n < min) return `Must be ${min} or more.`;
  if (max !== undefined && n > max) return `Must be ${max} or less.`;
  return null;
};

const pastDate = (v) => {
  if (!v) return null;
  const d = new Date(v);
  if (d > new Date()) return "Date can't be in the future.";
  return null;
};

// Compose several validators for one field; returns the first error found.
function compose(...fns) {
  return (v) => {
    for (const fn of fns) {
      const err = fn(v);
      if (err) return err;
    }
    return null;
  };
}

export const SECTIONS = [
  {
    section_name: "Promoter & Company Details",
    section_key: "promoter-company",
    intro: "Basic identity details every offer document opens with.",
    fields: [
      {
        field_key: "company_legal_name",
        clause_number: "Sch. VI, Part A, Cl. 7(A)",
        plain_language_prompt: "What is the full legal name of the company, exactly as registered?",
        field_type: "text",
        placeholder: "e.g. Aravalli Precision Components Limited",
        validate: compose(required("Company legal name")),
      },
      {
        field_key: "cin",
        clause_number: "Sch. VI, Part A, Cl. 7(A)",
        plain_language_prompt: "What is the company's Corporate Identity Number (CIN)?",
        field_type: "text",
        placeholder: "e.g. U29253MH2014PLC256321",
        helper: "21 characters, exactly as it appears on your incorporation certificate.",
        validate: compose(
          required("CIN"),
          pattern(CIN_RE, "Doesn't look like a valid 21-character CIN.")
        ),
      },
      {
        field_key: "registered_office_address",
        clause_number: "Sch. VI, Part A, Cl. 7(A)",
        plain_language_prompt: "What is the company's registered office address?",
        field_type: "textarea",
        placeholder: "Building, street, city, state, PIN code",
        validate: compose(required("Registered office address"), minLength(15)),
      },
      {
        field_key: "date_of_incorporation",
        clause_number: "Sch. VI, Part A, Cl. 1(a)",
        plain_language_prompt: "When was the company incorporated?",
        field_type: "date",
        validate: compose(required("Date of incorporation"), pastDate),
      },
      {
        field_key: "promoter_full_name",
        clause_number: "Sch. VI, Part A, Cl. 4(B)",
        plain_language_prompt: "What is the promoter's full name, as it appears on their PAN card?",
        field_type: "text",
        placeholder: "e.g. Rakesh Vinod Deshmukh",
        validate: compose(required("Promoter name")),
      },
      {
        field_key: "promoter_pan",
        clause_number: "Sch. VI, Part A, Cl. 7(A)",
        plain_language_prompt: "What is the promoter's PAN?",
        field_type: "text",
        placeholder: "e.g. ABCDE1234F",
        validate: compose(
          required("Promoter PAN"),
          pattern(PAN_RE, "PAN should look like ABCDE1234F.")
        ),
      },
      {
        field_key: "promoter_din",
        clause_number: "Sch. VI, Part A, Cl. 7(B)",
        plain_language_prompt: "If the promoter is also a director, what is their DIN? (Leave blank if not applicable.)",
        field_type: "text",
        placeholder: "e.g. 01234567",
        optional: true,
        validate: pattern(DIN_RE, "DIN should be 8 digits."),
      },
    ],
  },
  {
    section_name: "Business & Operations",
    section_key: "business-operations",
    intro: "How the company actually makes its money, in the promoter's own words.",
    fields: [
      {
        field_key: "nature_of_business",
        clause_number: "Sch. VI, Part A, Cl. 4(A)",
        plain_language_prompt: "In plain terms, what does the company do and who are its customers?",
        field_type: "textarea",
        placeholder: "Describe the business as you'd explain it to a new employee.",
        validate: compose(required("Nature of business"), minLength(50)),
      },
      {
        field_key: "key_products_services",
        clause_number: "Sch. VI, Part A, Cl. 4(A)",
        plain_language_prompt: "What are the company's main products or services?",
        field_type: "textarea",
        validate: compose(required("Key products/services"), minLength(20)),
      },
      {
        field_key: "manufacturing_locations",
        clause_number: "Sch. VI, Part A, Cl. 4(A)",
        plain_language_prompt: "Where are the company's manufacturing units or main places of operation?",
        field_type: "textarea",
        validate: compose(required("Manufacturing / operating locations")),
      },
      {
        field_key: "employee_count",
        clause_number: "Sch. VI, Part A, Cl. 4(A)",
        plain_language_prompt: "How many people does the company currently employ?",
        field_type: "number",
        placeholder: "e.g. 142",
        validate: compose(required("Employee count"), numberRange(1, 100000)),
      },
    ],
  },
  {
    section_name: "Objects of the Issue",
    section_key: "objects-of-issue",
    intro: "Why the company is raising money, and what it plans to do with it.",
    fields: [
      {
        field_key: "issue_size_cr",
        clause_number: "Sch. VI, Part A, Cl. 8(A)",
        plain_language_prompt: "What is the proposed issue size, in ₹ crore?",
        field_type: "number",
        placeholder: "e.g. 42.5",
        validate: compose(required("Issue size"), numberRange(0.5, 5000)),
      },
      {
        field_key: "objects_of_issue",
        clause_number: "Reg. 229, Sch. VI Cl. 9(A)",
        plain_language_prompt: "What will the company use the raised money for?",
        field_type: "textarea",
        placeholder: "e.g. Funding working capital, repaying a specific loan, setting up a new unit...",
        validate: compose(required("Objects of the issue"), minLength(60)),
      },
      {
        field_key: "proposed_utilization_schedule",
        clause_number: "Reg. 229, Sch. VI Cl. 9(A)",
        plain_language_prompt: "Roughly when do you expect to deploy the funds — a rough year-wise or milestone-wise breakdown is fine.",
        field_type: "textarea",
        validate: compose(required("Utilization schedule")),
      },
    ],
  },
  {
    section_name: "Promoter Shareholding History",
    section_key: "shareholding-history",
    intro: "How the promoter came to hold their current stake.",
    fields: [
      {
        field_key: "current_shareholding_pct",
        clause_number: "Sch. VI, Part A, Cl. 8(B)",
        plain_language_prompt: "What percentage of the company does the promoter currently hold?",
        field_type: "number",
        placeholder: "e.g. 68.4",
        validate: compose(required("Current shareholding %"), numberRange(0, 100)),
      },
      {
        field_key: "shareholding_acquisition_history",
        clause_number: "Sch. VI, Part A, Cl. 8(B)",
        plain_language_prompt: "How did the promoter acquire these shares — original allotment, purchase, transfer, bonus, etc.? A brief timeline is fine.",
        field_type: "textarea",
        validate: compose(required("Shareholding acquisition history"), minLength(30)),
      },
      {
        field_key: "lock_in_eligible_shares",
        clause_number: "Sch. VI, Part A, Cl. 8(B)",
        plain_language_prompt: "How many of the promoter's shares are eligible for the minimum promoter contribution lock-in?",
        field_type: "number",
        placeholder: "e.g. 1250000",
        validate: compose(required("Lock-in eligible shares"), numberRange(0)),
      },
    ],
  },
  {
    section_name: "Related Party Transactions",
    section_key: "related-party",
    intro: "Anything the company has transacted with promoters, group entities, or relatives.",
    fields: [
      {
        field_key: "related_party_relationship",
        clause_number: "Sch. VI, Part A, Cl. 4(K)",
        plain_language_prompt: "Does the company have any related party relationships to disclose?",
        field_type: "select",
        options: [
          { value: "", label: "Select one..." },
          { value: "none", label: "None" },
          { value: "subsidiary", label: "Subsidiary" },
          { value: "associate", label: "Associate company" },
          { value: "promoter-group", label: "Promoter group entity" },
          { value: "other", label: "Other" },
        ],
        validate: compose(required("Related party relationship")),
      },
      {
        field_key: "related_party_transactions",
        clause_number: "Sch. VI, Part A, Cl. 4(K)",
        plain_language_prompt: "Describe any transactions with related parties over the last 3 years (amounts, nature, parties involved). Write \"None\" if not applicable.",
        field_type: "textarea",
        validate: compose(required("Related party transactions")),
      },
    ],
  },
  {
    section_name: "Risk Factor Inputs",
    section_key: "risk-factors",
    intro: "Promoter-reported risks, in your own words — these get turned into formal risk factor drafting later.",
    fields: [
      {
        field_key: "operational_risks",
        clause_number: "Sch. VI, Part A, Cl. 5(B)",
        plain_language_prompt: "What operational risks worry you most (supply chain, key customers, key personnel, etc.)?",
        field_type: "textarea",
        validate: compose(required("Operational risks"), minLength(30)),
      },
      {
        field_key: "industry_risks",
        clause_number: "Sch. VI, Part A, Cl. 5(B)",
        plain_language_prompt: "What industry-wide or regulatory risks could affect the business?",
        field_type: "textarea",
        validate: compose(required("Industry risks"), minLength(30)),
      },
      {
        field_key: "litigation_disclosure",
        clause_number: "Sch. VI, Part A, Cl. 5(G)",
        plain_language_prompt: "Is the company, or any promoter/director, currently party to any litigation? Write \"None\" if not applicable.",
        field_type: "textarea",
        validate: compose(required("Litigation disclosure")),
      },
    ],
  },
  {
    section_name: "Management & Key Managerial Personnel",
    section_key: "management-kmp",
    intro: "Who runs the company day to day, and how the leadership team has changed.",
    fields: [
      {
        field_key: "board_composition",
        clause_number: "Sch. VI, Part A, Cl. 7(B)",
        plain_language_prompt: "Who are the company's directors? List each director's name, designation, and whether they are a promoter.",
        field_type: "textarea",
        placeholder: "e.g. Rakesh Deshmukh — Managing Director (Promoter); Anjali Rao — Independent Director",
        validate: compose(required("Board composition"), minLength(20)),
      },
      {
        field_key: "key_managerial_personnel",
        clause_number: "Sch. VI, Part A, Cl. 7(C)",
        plain_language_prompt: "Who are the company's key managerial personnel (CFO, Company Secretary, other senior leadership)? Include designation and relevant experience.",
        field_type: "textarea",
        validate: compose(required("Key managerial personnel"), minLength(20)),
      },
      {
        field_key: "director_relationships",
        clause_number: "Sch. VI, Part A, Cl. 7(B)",
        plain_language_prompt: "Are any directors related to each other or to the promoter (spouse, sibling, parent-child, etc.)? Write \"None\" if not applicable.",
        field_type: "textarea",
        validate: compose(required("Director relationships")),
      },
      {
        field_key: "management_changes_last_3_years",
        clause_number: "Sch. VI, Part A, Cl. 7(B)",
        plain_language_prompt: "Have there been any changes to the board or key managerial personnel in the last 3 years? Write \"None\" if not applicable.",
        field_type: "textarea",
        validate: compose(required("Management changes")),
      },
    ],
  },
  {
    section_name: "Statutory Approvals & Borrowings",
    section_key: "approvals-borrowings",
    intro: "The licenses that let the company operate, and what it currently owes.",
    fields: [
      {
        field_key: "material_licenses_approvals",
        clause_number: "Sch. VI, Part A, Cl. 5(G)",
        plain_language_prompt: "What material licenses, registrations, or approvals does the company hold to run its business (e.g. GST registration, factory license, industry-specific permits)?",
        field_type: "textarea",
        validate: compose(required("Material licenses & approvals"), minLength(20)),
      },
      {
        field_key: "pending_regulatory_approvals",
        clause_number: "Sch. VI, Part A, Cl. 5(G)",
        plain_language_prompt: "Are there any licenses or approvals the company has applied for but not yet received? Write \"None\" if not applicable.",
        field_type: "textarea",
        validate: compose(required("Pending regulatory approvals")),
      },
      {
        field_key: "outstanding_borrowings",
        clause_number: "Sch. VI, Part A, Cl. 4(F)",
        plain_language_prompt: "What are the company's outstanding borrowings — lender name, amount, and security offered (if any)? Write \"None\" if the company has no borrowings.",
        field_type: "textarea",
        validate: compose(required("Outstanding borrowings")),
      },
      {
        field_key: "contingent_liabilities",
        clause_number: "Sch. VI, Part A, Cl. 4(J)",
        plain_language_prompt: "Does the company have any contingent liabilities — guarantees given, disputed tax demands, unacknowledged claims? Write \"None\" if not applicable.",
        field_type: "textarea",
        validate: compose(required("Contingent liabilities")),
      },
    ],
  },
];

// Flat lookup, keyed by field_key — handy for validation and payload assembly.
export const ALL_FIELDS = SECTIONS.flatMap((s) =>
  s.fields.map((f) => ({ ...f, section_name: s.section_name }))
);