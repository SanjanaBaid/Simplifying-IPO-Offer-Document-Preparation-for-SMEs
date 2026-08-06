import { useState } from "react";
import PageShell from "../components/PageShell";
import apiClient from "../api/client";
import useCompanyId from "../hooks/useCompanyId";

const PRIORITY_STATUS_CLASS = { HIGH: "flag", MEDIUM: "pending", LOW: "clear" };

function moduleStatusClass(score, max) {
  if (max <= 0) return "pending";
  const ratio = score / max;
  if (ratio >= 0.8) return "clear";
  if (ratio >= 0.5) return "pending";
  return "flag";
}

function downloadBlob(data, filename, mimeType) {
  const blob = new Blob([data], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export default function Handoff() {
  const [companyId, setCompanyId] = useCompanyId();
  const [scorecard, setScorecard] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(null); // "pdf" | "json" | null
  const [errorMsg, setErrorMsg] = useState("");

  async function handleLoadScorecard() {
    if (!companyId) {
      setErrorMsg("Enter a company ID above before loading the scorecard.");
      return;
    }
    setLoading(true);
    setErrorMsg("");
    try {
      const { data } = await apiClient.get(
        `/handoff/scorecard?company_id=${encodeURIComponent(companyId)}`
      );
      setScorecard(data);
    } catch (err) {
      setErrorMsg(
        err.response?.data?.detail ||
          "Couldn't load the scorecard — confirm the company_id is correct and the backend is running."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleExport(format) {
    if (!companyId) {
      setErrorMsg("Enter a company ID above before exporting.");
      return;
    }
    setExporting(format);
    setErrorMsg("");
    try {
      const response = await apiClient.post(
        `/handoff/export?company_id=${encodeURIComponent(companyId)}&export_format=${format}`,
        null,
        { responseType: format === "pdf" ? "blob" : "json" }
      );

      if (format === "pdf") {
        const disposition = response.headers["content-disposition"] || "";
        const match = disposition.match(/filename="?([^"]+)"?/);
        const filename = match ? match[1] : `${companyId}_handoff.pdf`;
        downloadBlob(response.data, filename, "application/pdf");
      } else {
        downloadBlob(
          JSON.stringify(response.data, null, 2),
          `${companyId}_handoff.json`,
          "application/json"
        );
      }

      // A successful export recomputes the score server-side too — refresh so
      // the on-screen scorecard matches what just got packaged.
      const { data } = await apiClient.get(
        `/handoff/scorecard?company_id=${encodeURIComponent(companyId)}`
      );
      setScorecard(data);
    } catch (err) {
      setErrorMsg(
        err.response?.data?.detail ||
          `Couldn't export the ${format.toUpperCase()} package — confirm the backend is running.`
      );
    } finally {
      setExporting(null);
    }
  }

  const gapsByPriority = { HIGH: [], MEDIUM: [], LOW: [] };
  (scorecard?.gap_list || []).forEach((g) => {
    (gapsByPriority[g.priority] || gapsByPriority.LOW).push(g);
  });

  return (
    <PageShell
      eyebrow="Module 05 — Summit"
      title="Merchant Banker Handoff"
      sub="Packages the drafted sections, consistency report, and gap list into a single review-ready bundle for the merchant banker."
    >
      <div className="company-bar">
        <label htmlFor="company-id">Company ID</label>
        <input
          id="company-id"
          type="text"
          className="intake-input"
          placeholder="Paste the company_id to build a handoff package for"
          value={companyId}
          onChange={(e) => setCompanyId(e.target.value.trim())}
        />
        <span className="company-bar-hint">
          Rolls up Intake, Drafting, Consistency, and Risk Audit completeness into one score.
        </span>
      </div>

      {errorMsg && <p className="field-error">{errorMsg}</p>}

      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        <button type="button" className="btn-primary" onClick={handleLoadScorecard} disabled={loading}>
          {loading ? "Loading…" : scorecard ? "Refresh scorecard" : "Load scorecard"}
        </button>
        <button
          type="button"
          className="btn-ghost"
          onClick={() => handleExport("pdf")}
          disabled={exporting !== null}
        >
          {exporting === "pdf" ? "Generating PDF…" : "Download PDF package"}
        </button>
        <button
          type="button"
          className="btn-ghost"
          onClick={() => handleExport("json")}
          disabled={exporting !== null}
        >
          {exporting === "json" ? "Generating JSON…" : "Download JSON package"}
        </button>
      </div>

      {scorecard && (
        <>
          <div className="mock-card" style={{ marginTop: "1.5rem", marginBottom: "1.5rem" }}>
            <span className={`status ${moduleStatusClass(scorecard.total_score, 100)}`}>
              {scorecard.total_score}/100
            </span>
            <h3>{scorecard.company_name} — overall readiness</h3>
            <p>
              {scorecard.gap_list.length} gap{scorecard.gap_list.length === 1 ? "" : "s"} outstanding
              across intake, drafting, consistency, and risk audit.
            </p>
          </div>

          <div className="mock-grid" style={{ marginBottom: "1.5rem" }}>
            {scorecard.modules.map((m) => (
              <div className="mock-card" key={m.module}>
                <span className={`status ${moduleStatusClass(m.score, m.max)}`}>
                  {m.score}/{m.max}
                </span>
                <h3>{m.module}</h3>
                <p>{m.note}</p>
              </div>
            ))}
          </div>

          {scorecard.gap_list.length > 0 ? (
            <div className="mock-card">
              <span className="status flag">
                {scorecard.gap_list.length} item{scorecard.gap_list.length === 1 ? "" : "s"} before
                handoff
              </span>
              <h3>Prioritised gap list</h3>

              {["HIGH", "MEDIUM", "LOW"].map((priority) =>
                gapsByPriority[priority].length > 0 ? (
                  <div key={priority} style={{ marginTop: "1rem" }}>
                    <p className="pane-eyebrow" style={{ marginBottom: "0.5rem" }}>
                      {priority} priority
                    </p>
                    <div className="review-grid">
                      {gapsByPriority[priority].map((g, i) => (
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
                ) : null
              )}
            </div>
          ) : (
            <p className="placeholder-note">
              No outstanding gaps — this company is ready to package for the merchant banker.
            </p>
          )}
        </>
      )}

      {!scorecard && !loading && (
        <p className="placeholder-note" style={{ marginTop: "1.5rem" }}>
          Load the scorecard to see completeness across every module, or export directly — export
          always recomputes the score first.
        </p>
      )}
    </PageShell>
  );
}