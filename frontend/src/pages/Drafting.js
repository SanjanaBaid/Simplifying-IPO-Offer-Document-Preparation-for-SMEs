import { useEffect, useState } from "react";
import PageShell from "../components/PageShell";
import apiClient from "../api/client";
import useCompanyId from "../hooks/useCompanyId";
import { renderInlineMarkdown } from "../utils/inlinemarkdown";


const SECTIONS = [
  { key: "general_information", label: "General Information" },
  { key: "business_overview", label: "Business Overview" },
  { key: "objects_of_issue", label: "Objects of the Issue" },
  { key: "risk_factors", label: "Risk Factors" },
  { key: "capital_structure", label: "Capital Structure" },
];

export default function Drafting() {
  const [companyId] = useCompanyId();
  const [drafts, setDrafts] = useState({}); 
  const [generating, setGenerating] = useState(null); 
  const [errorMsg, setErrorMsg] = useState("");
  const [classification, setClassification] = useState(null); 
  const [classifying, setClassifying] = useState(false);
  const [classifyError, setClassifyError] = useState("");
  const [loadingExisting, setLoadingExisting] = useState(true);

  // Reload whatever's already been generated/classified for this company —
  // otherwise this page renders blank on every remount (e.g. navigating to
  // another tab and back) even though the drafts are sitting in the database.
  useEffect(() => {
    if (!companyId) {
      setLoadingExisting(false);
      return;
    }
    let cancelled = false;
    setLoadingExisting(true);

    apiClient
      .get(`/drafting/sections?company_id=${encodeURIComponent(companyId)}`)
      .then(({ data }) => {
        if (cancelled) return;
        const bySectionKey = {};
        data.forEach((draft) => {
          bySectionKey[draft.section_key] = draft;
        });
        setDrafts(bySectionKey);
      })
      .catch(() => {
        // No drafts yet is a normal, silent state — the "Not drafted yet"
        // card already communicates that.
      })
      .finally(() => {
        if (!cancelled) setLoadingExisting(false);
      });

    apiClient
      .get(`/classifier/classify-risks/latest?company_id=${encodeURIComponent(companyId)}`)
      .then(({ data }) => {
        if (!cancelled) setClassification(data);
      })
      .catch(() => {
        // No saved classification yet — fine, leave it unset.
      });

    return () => {
      cancelled = true;
    };
  }, [companyId]);

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
      if (section.key === "risk_factors") {
        setClassification(null); 
      }
    } catch (err) {
      setErrorMsg(
        err.response?.data?.detail ||
          "Couldn't generate this section — confirm the backend is running and the knowledge base has been ingested."
      );
    } finally {
      setGenerating(null);
    }
  }

  async function handleClassify() {
    if (!companyId) {
      setClassifyError("Enter a company ID above before classifying.");
      return;
    }
    setClassifying(true);
    setClassifyError("");
    try {
      const { data } = await apiClient.post(
        `/classifier/classify-risks?company_id=${encodeURIComponent(companyId)}`
      );
      setClassification(data);
    } catch (err) {
      setClassifyError(
        err.response?.data?.detail ||
          "Couldn't classify risk factors — confirm a Risk Factors draft exists for this company."
      );
    } finally {
      setClassifying(false);
    }
  }

  return (
    <PageShell
      eyebrow="Module 02 — Camp II"
      title="Drafting Engine"
      sub="Generates DRHP sections from your intake answers and retrieved Schedule VI clauses, each drafted sentence traceable back to its source."
    >
      {errorMsg && <p className="field-error">{errorMsg}</p>}
      {loadingExisting && <p className="placeholder-note">Loading previously generated drafts…</p>}

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
                  <p style={{ whiteSpace: "pre-wrap" }}>{renderInlineMarkdown(draft.content)}</p>

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

                  {section.key === "risk_factors" && (
                    <div style={{ marginTop: "0.75rem" }}>
                      <button
                        type="button"
                        className="btn-ghost"
                        onClick={handleClassify}
                        disabled={classifying}
                      >
                        {classifying
                          ? "Classifying…"
                          : classification
                          ? "Re-classify risk factors"
                          : "Classify risk factors"}
                      </button>
                      {classifyError && <p className="field-error">{classifyError}</p>}
                    </div>
                  )}

                  {section.key === "risk_factors" && classification && (
                    <div style={{ marginTop: "1rem" }}>
                      <p className="pane-eyebrow" style={{ marginBottom: "0.5rem" }}>
                        Classified · v{classification.version} ·{" "}
                        {classification.flagged_count} of {classification.items.length} flagged
                      </p>
                      {classification.items.map((item, i) => (
                        <div
                          key={i}
                          className="review-card"
                          style={{ marginBottom: "0.5rem" }}
                        >
                          <div className="review-card-head">
                            <span
                              className={`status ${
                                item.needs_promoter_input ? "flag" : "clear"
                              }`}
                            >
                              {item.needs_promoter_input
                                ? "Needs promoter input"
                                : "Specific"}
                            </span>
                            <span className="review-clause">
                              Specificity {item.specificity_score}
                              {!item.scored_with_llm && " (heuristic)"}
                            </span>
                          </div>
                          <p style={{ margin: 0 }}>{renderInlineMarkdown(item.text)}</p>
                          {item.matched_phrases.length > 0 && (
                            <p className="field-helper">
                              Boilerplate phrases: {item.matched_phrases.join(", ")}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
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

      {classification && classification.flagged_count > 0 && (
        <div className="mock-card" style={{ marginTop: "1.5rem" }}>
          <span className="status flag">
            {classification.flagged_count} item
            {classification.flagged_count === 1 ? "" : "s"} need promoter input
          </span>
          <h3>Needs promoter input queue</h3>
          <p>
            These risk factors read as generic or boilerplate — go back to Intake and add
            specifics (numbers, named suppliers/customers, dates) for each.
          </p>
          <ul>
            {classification.items
              .filter((item) => item.needs_promoter_input)
              .map((item, i) => (
                <li key={i} style={{ marginBottom: "0.5rem" }}>
                  {renderInlineMarkdown(item.text)}
                </li>
              ))}
          </ul>
        </div>
      )}
    </PageShell>
  );
}