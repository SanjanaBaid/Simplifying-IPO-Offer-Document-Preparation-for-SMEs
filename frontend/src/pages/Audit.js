import { useState } from "react";
import PageShell from "../components/PageShell";
import apiClient from "../api/client";
import useCompanyId from "../hooks/useCompanyId";

const STATUS_LABEL = { clear: "Satisfied", pending: "Partial", flag: "Gap found" };
const PRIORITY_STATUS_CLASS = { HIGH: "flag", MEDIUM: "pending", LOW: "clear" };

export default function Audit() {
  const [companyId, setCompanyId] = useCompanyId();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  async function handleRunAudit() {
    if (!companyId) {
      setErrorMsg("Enter a company ID above before running the audit.");
      return;
    }
    setLoading(true);
    setErrorMsg("");
    try {
      const { data } = await apiClient.get(
        `/audit/report?company_id=${encodeURIComponent(companyId)}`
      );
      setReport(data);
    } catch (err) {
      setErrorMsg(
        err.response?.data?.detail ||
          "Couldn't run the audit — confirm the company_id is correct and the backend is running."
      );
    } finally {
      setLoading(false);
    }
  }

  const totalGaps = report
    ? report.sections.reduce((sum, s) => sum + s.items.length, 0)
    : 0;

  return (
    <PageShell
      eyebrow="Module 04 — Camp IV"
      title="Risk & Completeness Auditor"
      sub="Runs the near-final draft against ICDR Schedule VI and SME Chapter IX requirements, surfacing gaps before merchant banker review."
    >
      <div className="company-bar">
        <label htmlFor="company-id">Company ID</label>
        <input
          id="company-id"
          type="text"
          className="intake-input"
          placeholder="Paste the company_id to audit"
          value={companyId}
          onChange={(e) => setCompanyId(e.target.value.trim())}
        />
        <span className="company-bar-hint">
          Rolls up Intake, Drafting, Consistency, and Risk Audit — plus an explicit Schedule VI
          clause-citation check the handoff scorecard doesn't do.
        </span>
      </div>

      {errorMsg && <p className="field-error">{errorMsg}</p>}

      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
        <button type="button" className="btn-primary" onClick={handleRunAudit} disabled={loading}>
          {loading ? "Auditing…" : report ? "Re-run audit" : "Run audit"}
        </button>
      </div>

      {report && (
        <>
          <div className="mock-card" style={{ marginBottom: "1.5rem" }}>
            <span className={`status ${report.total_score >= 80 ? "clear" : report.total_score >= 50 ? "pending" : "flag"}`}>
              {report.total_score}/100
            </span>
            <h3>{report.company_name} — audit readiness</h3>
            <p>
              {report.clause_coverage.cited_count} of {report.clause_coverage.total_fields} Schedule
              VI clauses ({report.clause_coverage.coverage_pct}%) are answered and actually cited in
              a drafted section. {report.clause_coverage.answered_count} of{" "}
              {report.clause_coverage.total_fields} are answered at all. {totalGaps} finding
              {totalGaps === 1 ? "" : "s"} below.
            </p>
          </div>

          <div className="mock-grid" style={{ marginBottom: "1.5rem" }}>
            {report.sections.map((s) => (
              <div className="mock-card" key={s.name}>
                <span className={`status ${s.status}`}>{STATUS_LABEL[s.status]}</span>
                <h3>{s.name}</h3>
                <p>
                  {s.items.length === 0
                    ? "No findings in this section."
                    : `${s.items.length} finding${s.items.length === 1 ? "" : "s"} to review.`}
                </p>
              </div>
            ))}
          </div>

          {totalGaps > 0 ? (
            report.sections
              .filter((s) => s.items.length > 0)
              .map((s) => (
                <div className="mock-card" key={s.name} style={{ marginBottom: "1rem" }}>
                  <span className={`status ${s.status}`}>{s.name}</span>
                  <h3>{s.name} findings</h3>
                  <div className="review-grid" style={{ marginTop: "0.75rem" }}>
                    {s.items.map((g, i) => (
                      <div className="review-card" key={i}>
                        <div className="review-card-head">
                          <h3>{g.module}</h3>
                          <span className={`status ${PRIORITY_STATUS_CLASS[g.priority]}`}>
                            {g.priority}
                          </span>
                        </div>
                        <p style={{ margin: 0 }}>{g.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))
          ) : (
            <p className="placeholder-note">
              No outstanding findings — this company clears the audit against ICDR Schedule VI and
              SME Chapter IX requirements.
            </p>
          )}
        </>
      )}

      {!report && !loading && (
        <p className="placeholder-note" style={{ marginTop: "1.5rem" }}>
          Run the audit to see real findings, including clause-level citation coverage — no mock
          data.
        </p>
      )}
    </PageShell>
  );
}
