import { useState } from "react";
import PageShell from "../components/PageShell";
import apiClient from "../api/client";
import useCompanyId from "../hooks/useCompanyId";


const SECTIONS = [
  { key: "risk_factors", label: "Risk Factors" },
  { key: "capital_structure", label: "Capital Structure" },
];

export default function Drafting() {
  const [companyId, setCompanyId] = useCompanyId();
  const [drafts, setDrafts] = useState({}); // section key -> response object
  const [generating, setGenerating] = useState(null); // section key in flight
  const [errorMsg, setErrorMsg] = useState("");

  async function handleGenerate(section) {
    if (!companyId) {
      setErrorMsg("Enter a company ID above before generating a section.");
      return;
    }

    setGenerating(section.key);
    setErrorMsg("");
    try {
      const { data } = await apiClient.post("/drafting/generate", {
        company_id: companyId,
        section: section.key,
      });
      setDrafts((prev) => ({ ...prev, [section.key]: data }));
    } catch (err) {
      setErrorMsg(
        err.response?.data?.detail ||
          "Couldn't generate this section — confirm the backend is running and the knowledge base has been ingested."
      );
    } finally {
      setGenerating(null);
    }
  }

  return (
    <PageShell
      eyebrow="Module 02 — Camp II"
      title="Drafting Engine"
      sub="Generates DRHP sections from your intake answers and retrieved Schedule VI clauses, each drafted sentence traceable back to its source."
    >
      <div className="company-bar">
        <label htmlFor="company-id">Company ID</label>
        <input
          id="company-id"
          type="text"
          className="intake-input"
          placeholder="Paste the company_id whose intake you want drafted"
          value={companyId}
          onChange={(e) => setCompanyId(e.target.value.trim())}
        />
        <span className="company-bar-hint">
          Same company_id used on the Intake page — the draft is built from that company's
          saved answers and uploaded financials.
        </span>
      </div>

      {errorMsg && <p className="field-error">{errorMsg}</p>}

      <div className="mock-grid">
        {SECTIONS.map((section) => {
          const draft = drafts[section.key];
          const isGenerating = generating === section.key;
          const hasGaps = draft?.missing_intake_fields?.length > 0;

          return (
            <div className="mock-card" key={section.key}>
              <span className={`status ${draft ? (hasGaps ? "flag" : "clear") : "pending"}`}>
                {draft ? `Drafted · v${draft.version}` : "Not drafted yet"}
              </span>
              <h3>{section.label}</h3>

              {draft ? (
                <>
                  {draft.schedule_vi_clause && (
                    <p className="clause-tag">{draft.schedule_vi_clause}</p>
                  )}
                  <p style={{ whiteSpace: "pre-wrap" }}>{draft.content}</p>

                  {hasGaps && (
                    <p className="field-error">
                      Needs promoter input: {draft.missing_intake_fields.join(", ")}
                    </p>
                  )}

                  {draft.retrieved_clauses?.length > 0 && (
                    <details>
                      <summary style={{ cursor: "pointer" }}>
                        {draft.retrieved_clauses.length} clause
                        {draft.retrieved_clauses.length === 1 ? "" : "s"} retrieved
                      </summary>
                      <ul style={{ marginTop: "0.5rem" }}>
                        {draft.retrieved_clauses.map((c) => (
                          <li key={c.id || c.clause_number}>
                            <span className="clause-tag">{c.clause_number}</span>
                            <span> {c.source}</span>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                </>
              ) : (
                <p>Not generated yet — complete Guided Intake first, then generate.</p>
              )}

              <button
                type="button"
                className="btn-primary"
                onClick={() => handleGenerate(section)}
                disabled={isGenerating}
              >
                {isGenerating
                  ? "Generating…"
                  : draft
                  ? `Regenerate ${section.label}`
                  : `Generate ${section.label}`}
              </button>
            </div>
          );
        })}
      </div>

      <p className="placeholder-note">
        Each drafted sentence cites the Schedule VI clause it was grounded in. If a section
        looks thin, check the "Needs promoter input" line — it means the underlying intake
        answer was blank, not that the engine failed.
      </p>
    </PageShell>
  );
}