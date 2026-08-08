# Sherpa — SME IPO Offer Document Drafting Copilot

**Sherpa drafts. The merchant banker still reviews, certifies, and files.**

Sherpa is a RAG-powered drafting copilot that helps SME issuers and their merchant bankers
produce a SEBI ICDR / Schedule VI–compliant Draft Red Herring Prospectus (DRHP) — turning a
guided, plain-language intake into cited, auditable draft sections, and catching boilerplate
risk factors and narrative-vs-financials mismatches before SEBI does.

---

## The problem

SME IPO offer documents are expensive and slow to prepare because every disclosure has to be
mapped to a specific Schedule VI clause, every risk factor has to be specific rather than
generic boilerplate, and every number quoted in the narrative has to tie back to the audited
financials. Today this is done almost entirely by hand, or through expensive advisory
retainers. Sherpa automates the first draft and the first-pass quality check, so the merchant
banker's review starts from a much stronger baseline.

## What Sherpa does

| Module | What it does |
|---|---|
| **Guided Intake** | A plain-language questionnaire maps 1:1 onto Schedule VI data fields, so promoters answer in their own words while the system tracks exactly which regulatory clause each answer feeds. |
| **AI Draft** | Retrieval-augmented generation over an embedded SEBI ICDR / Schedule VI / SME Chapter IX knowledge base drafts sections (Risk Factors, Capital Structure, …) from the promoter's intake answers, with every clause cited inline. |
| **Consistency Checker** | Parses numeric claims out of the drafted narrative, cross-references them against financial statement line items extracted from the uploaded PDF, and flags variances beyond a configurable materiality threshold — plus cross-foot and structural sanity checks. |
| **Risk & Completeness Auditor** | Classifies each drafted risk factor as specific or boilerplate (rule-based phrase detection + LLM specificity scoring), and rolls up Schedule VI clause coverage, drafting completeness, risk specificity, and financial consistency into one audit report. |
| **Scorecard & Handoff** | A 100-point completeness scorecard (20 points each across Intake, Drafting, Consistency, and Risk Audit, plus a Handoff-readiness score) with a prioritised HIGH/MEDIUM/LOW gap list, exportable as a merchant-banker handoff package in JSON or PDF. |

All five modules sit behind promoter authentication, with a merchant-banker dashboard listing
every active SME mandate.

## Architecture

```
┌─────────────────────────┐        ┌──────────────────────────────────────┐
│   React frontend         │        │   FastAPI backend                      │
│   (sign-in, dashboard,    │  HTTP  │                                         │
│   5-module workspace)     │◄──────►│  auth · api · drafting · classifier    │
│                            │        │  consistency · audit · handoff         │
└─────────────────────────┘        └───────────────┬────────────────────────┘
                                                       │
                                     ┌─────────────────┼─────────────────┐
                                     ▼                 ▼                 ▼
                              ┌───────────┐    ┌──────────────┐  ┌─────────────┐
                              │ SQLite /   │    │  ChromaDB     │  │  Groq API    │
                              │ SQLAlchemy │    │  (regulation  │  │  (LLM         │
                              │  (app data)│    │   embeddings) │  │   drafting)   │
                              └───────────┘    └──────────────┘  └─────────────┘
```

## Tech stack

- **Backend:** FastAPI, SQLAlchemy, ChromaDB (vector store), PyMuPDF (PDF parsing/generation), bcrypt, Groq API (LLM)
- **Frontend:** React, React Router, Axios
- **Data:** SQLite by default (via SQLAlchemy, swappable), ChromaDB for embedded regulation clauses

## Repository structure

```
backend/
  main.py                    FastAPI app + router registration
  models.py                  SQLAlchemy schema (Promoters, Companies, Sessions,
                              Intake, Schedule VI Fields, Financials, Draft
                              Sections, Risk Classifications, ...)
  database.py                Engine / session setup
  schemas.py                 Shared Pydantic schemas

  auth.py                    Promoter signup/login/session auth + mandate
                              (company) create/list API
  api.py                     Intake submission + financial statement upload
                              and line-item extraction
  ingest.py                  CLI: chunk + embed a regulation source file into
                              ChromaDB
  drafting.py                RAG retrieval + LLM drafting engine, per-section
                              prompt templates, draft versioning
  classifier.py               Boilerplate risk-factor classifier
  consistency.py             Narrative-vs-financials consistency checker
  audit.py                   Risk & Completeness audit report (Schedule VI
                              clause coverage + regrouped gap list)
  handoff.py                 100-point scorecard + JSON/PDF handoff export

  seed_schedule_vi_fields.py  Seeds the 22-field Schedule VI catalogue
  seed_dev.py                  Minimal dev company/promoter seed
  seed_demo.py                 Full hardcoded demo scenario (sample SME
                                manufacturer, guaranteed boilerplate flag +
                                guaranteed consistency mismatch, for reliable
                                live demos)
  regulations/                 Sample regulation source text for ingest.py

frontend/
  src/
    context/AuthContext.js     Session state, signup/login/logout
    components/TopNav.js       Brand + module tabs + signed-in promoter chip
    components/PageShell.js    Shared page layout for the 5 modules
    hooks/useCompanyId.js      Reads the active company_id from the route
    pages/
      Login.js, Signup.js      Auth screens
      Dashboard.js             Active SME mandates list + new mandate form
      Intake.js                Guided intake questionnaire
      Drafting.js              AI draft generation + display
      Consistency.js           Consistency checker UI
      Audit.js                 Risk & completeness audit report UI
      Handoff.js                Scorecard + handoff export UI
```

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 18+
- A free [Groq API key](https://console.groq.com/keys) (optional — the drafting engine
  falls back to a labeled stub draft without one, useful for testing the rest of the
  pipeline without a key)

### Backend

```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in `backend/` (never commit this):

```
GROQ_API_KEY=your_key_here
```

Seed the Schedule VI field catalogue (required — the intake API has nothing to map
answers to without this):

```bash
python seed_schedule_vi_fields.py
```

Ingest a regulation source file into ChromaDB (required before `/drafting/generate` will
work — `regulations/` includes a sample source in the correct `[CLAUSE ...]` format):

```bash
python ingest.py --source regulations/icdr_schedule_vi_sample.txt
```

Optionally seed a full demo scenario (a complete sample company with intake answers,
drafted sections, and financials — useful for trying the app immediately):

```bash
python seed_demo.py
```

Start the API:

```bash
python -m uvicorn main:app --reload
```

The interactive API docs are at **http://127.0.0.1:8000/docs**.

### Frontend

```bash
cd frontend
npm install
npm start
```

The app runs at **http://localhost:3000** and expects the backend at
`http://127.0.0.1:8000` (see `frontend/src/api/client.js`).

## Demo accounts

If you ran `seed_demo.py`, sign in with:

| Email | Password |
|---|---|
| `ashwin.kulkarni@aravalli-demo.example` | `demopassword` |

If you ran `seed_dev.py` instead:

| Email | Password |
|---|---|
| `dev-promoter@example.com` | `devpassword` |

## API reference

All endpoints except `/auth/signup` and `/auth/login` require a promoter session — pass
`Authorization: Bearer <token>` (the frontend does this automatically once signed in).

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/signup` | Create a promoter account |
| POST | `/auth/login` | Sign in, get a session token |
| POST | `/auth/logout` | Invalidate the current session |
| GET | `/auth/me` | Current signed-in promoter |
| GET | `/companies` | List the signed-in promoter's SME mandates |
| POST | `/companies` | Create a new mandate |
| GET / POST | `/intake` | Get / submit guided intake answers for a company |
| GET | `/financials` | List extracted financial line items for a company |
| POST | `/upload-financials` | Upload a financial statement PDF for line-item extraction (native text-layer PDFs only — no OCR yet) |
| POST | `/drafting/generate` | Generate (or re-generate) a drafted section |
| GET | `/drafting/sections` | List all drafted sections for a company |
| GET | `/drafting/clauses` | Query the embedded regulation knowledge base directly |
| POST | `/classifier/classify-risks` | Classify the latest Risk Factors draft |
| GET | `/classifier/classify-risks/latest` | Get the latest classification result |
| POST | `/consistency/check` | Run the narrative-vs-financials consistency check |
| GET | `/audit/report` | Full Schedule VI coverage + regrouped audit report |
| GET | `/handoff/scorecard` | 100-point completeness scorecard |
| POST | `/handoff/export` | Export the handoff package (`?export_format=json\|pdf`) |

## Contributors

- [Sanjana Baid](https://github.com/SanjanaBaid)
- [ankitaak2312](https://github.com/ankitaak2312)

## License

MIT — see [LICENSE](./LICENSE).
