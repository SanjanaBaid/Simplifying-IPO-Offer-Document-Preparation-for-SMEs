import { useState } from "react";
import PageShell from "../components/PageShell";
import apiClient from "../api/client";
import useCompanyId from "../hooks/useCompanyId";
import { renderInlineMarkdown } from "../utils/inlinemarkdown";

const CLAIM_STATUS_LABEL = {
  match: "Consistent",
  mismatch: "Mismatch",
  unmatched: "No financial match",
};

const CLAIM_STATUS_CLASS = {
  match: "clear",
  mismatch: "flag",
  unmatched: "pending",
};

export default function Consistency() {
  const [companyId] = useCompanyId();
  const [threshold, setThreshold] = useState(1.0);
  const [result, setResult] = useState(null);
  const [checking, setChecking] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  async function runCheck(thresholdValue, { silent = false } = {}) {
    if (!companyId) {
      if (!silent) setErrorMsg("Enter a company ID above before running the checker.");
      return;
    }
    setChecking(true);
    if (!silent) setErrorMsg("");
    try {
      const { data } = await apiClient.post(
        `/consistency/check?company_id=${encodeURIComponent(companyId)}&materiality_threshold_pct=${thresholdValue}`
      );
      setResult(data);
    } catch (err) {
      // On the silent auto-run, "nothing to check yet" (404) is a normal,
      // quiet state — the placeholder note below already covers it.
      if (!silent || err.response?.status !== 404) {
        setErrorMsg(
          err.response?.data?.detail ||
            "Couldn't run the consistency check — confirm drafted sections and uploaded financials exist for this company."
        );
      }
    } finally {
      setChecking(false);
    }
  }

  function handleCheck() {
    return runCheck(threshold);
  }

  const flaggedClaims = result?.numeric_claims?.filter((c) => c.status === "mismatch") || [];
  const otherClaims = result?.numeric_claims?.filter((c) => c.status !== "mismatch") || [];

  return (
    <PageShell
      eyebrow="Module 03 — Camp III"
      title="Consistency Checker"
      sub="Cross-references figures drafted in the narrative against every extracted financial line item, flagging mismatches before they reach the auditor."
    >
      <div className="company-bar">
        <label htmlFor="threshold">Materiality threshold (%)</label>
        <input
          id="threshold"
          type="number"
          min="0"
          step="0.1"
          className="intake-input"
          style={{ maxWidth: "120px" }}
          value={threshold}
          onChange={(e) => setThreshold(e.target.value === "" ? "" : Number(e.target.value))}
        />
        <span className="company-bar-hint">
          Variances at or below this % are treated as rounding noise, not mismatches.
        </span>
      </div>

      {errorMsg && <p className="field-error">{errorMsg}</p>}

      <button type="button" className="btn-primary" onClick={handleCheck} disabled={checking}>
        {checking ? "Checking…" : result ? "Re-run consistency check" : "Run consistency check"}
      </button>

      {result && (
        <>
          <p className="placeholder-note" style={{ marginTop: "1rem" }}>
            {result.flagged_count} issue{result.flagged_count === 1 ? "" : "s"} flagged across{" "}
            {result.sections_checked.join(", ")} · threshold {result.materiality_threshold_pct}%
          </p>

          {flaggedClaims.length > 0 && (
            <div className="mock-card" style={{ marginBottom: "1.5rem" }}>
              <span className="status flag">
                {flaggedClaims.length} number{flaggedClaims.length === 1 ? "" : "s"} don't tie out
              </span>
              <h3>Numeric mismatches</h3>
              <div className="review-grid">
                {flaggedClaims.map((claim, i) => (
                  <div className="review-card" key={i}>
                    <div className="review-card-head">
                      <h3>{claim.claimed_label}</h3>
                      <span className="status flag">Mismatch</span>
                    </div>
                    {claim.schedule_vi_clause && (
                      <p className="clause-tag">{claim.schedule_vi_clause}</p>
                    )}
                    <div className="review-row">
                      <span className="review-clause">Drafted as</span>
                      <span className="review-value">
                        {claim.claimed_value}
                        {claim.is_percent ? "%" : ""} ({claim.draft_section} v{claim.draft_version})
                      </span>
                    </div>
                    <div className="review-row">
                      <span className="review-clause">Financials say</span>
                      <span className="review-value">
                        {claim.matched_line_item_value} — {claim.matched_line_item_label}
                        {claim.matched_line_item_period ? ` (${claim.matched_line_item_period})` : ""}
                      </span>
                    </div>
                    <div className="review-row">
                      <span className="review-clause">Variance</span>
                      <span className="review-value">{claim.variance_pct}%</span>
                    </div>
                    <p className="field-helper">"{renderInlineMarkdown(claim.snippet)}"</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(result.crossfoot_checks.length > 0 || result.ratio_checks.length > 0) && (
            <div className="mock-grid" style={{ marginBottom: "1.5rem" }}>
              {result.crossfoot_checks.map((c, i) => (
                <div className="mock-card" key={`cf-${i}`}>
                  <span className={`status ${c.flagged ? "flag" : "clear"}`}>
                    {c.flagged ? "Doesn't foot" : "Foots correctly"}
                  </span>
                  <h3>{c.total_label}</h3>
                  <p>
                    Reported {c.reported_total} vs. computed sum {c.computed_sum} of{" "}
                    {c.component_labels.join(", ")} — {c.variance_pct}% variance ({c.period}).
                  </p>
                </div>
              ))}
              {result.ratio_checks.map((r, i) => (
                <div className="mock-card" key={`ratio-${i}`}>
                  <span className={`status ${r.flagged ? "flag" : "clear"}`}>
                    {r.flagged ? "Failed" : "Passed"}
                  </span>
                  <h3>{r.check_name}</h3>
                  <p>{r.detail}</p>
                </div>
              ))}
            </div>
          )}

          {otherClaims.length > 0 && (
            <details>
              <summary style={{ cursor: "pointer" }}>
                {otherClaims.length} other drafted figure{otherClaims.length === 1 ? "" : "s"} checked
              </summary>
              <div className="review-grid" style={{ marginTop: "0.75rem" }}>
                {otherClaims.map((claim, i) => (
                  <div className="review-card" key={i}>
                    <div className="review-card-head">
                      <h3>{claim.claimed_label}</h3>
                      <span className={`status ${CLAIM_STATUS_CLASS[claim.status]}`}>
                        {CLAIM_STATUS_LABEL[claim.status]}
                      </span>
                    </div>
                    {claim.schedule_vi_clause && (
                      <p className="clause-tag">{claim.schedule_vi_clause}</p>
                    )}
                    <div className="review-row">
                      <span className="review-clause">Drafted as</span>
                      <span className="review-value">
                        {claim.claimed_value}
                        {claim.is_percent ? "%" : ""}
                      </span>
                    </div>
                    {claim.matched_line_item_label && (
                      <div className="review-row">
                        <span className="review-clause">Financials say</span>
                        <span className="review-value">
                          {claim.matched_line_item_value} — {claim.matched_line_item_label}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </details>
          )}
        </>
      )}

      {!result && !checking && (
        <p className="placeholder-note">
          Run the checker to diff drafted narrative figures against extracted financial line
          items — nothing is checked until you press the button above.
        </p>
      )}
    </PageShell>
  );
}