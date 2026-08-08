import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import apiClient from "../api/client";
import { renderInlineMarkdown } from "../utils/inlinemarkdown";

function moduleStatusClass(score, max) {
  const pct = max ? score / max : 0;
  if (pct >= 0.8) return "clear";
  if (pct >= 0.4) return "pending";
  return "flag";
}

const PRIORITY_STATUS_CLASS = { HIGH: "flag", MEDIUM: "pending", LOW: "clear" };

export default function BankerMandate() {
  const { companyId } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  const [status, setStatus] = useState("reviewed");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitMsg, setSubmitMsg] = useState("");

  function load() {
    setLoading(true);
    setErrorMsg("");
    apiClient
      .get(`/banker/mandates/${companyId}`)
      .then(({ data }) => setDetail(data))
      .catch((err) => setErrorMsg(err.response?.data?.detail || "Couldn't load this mandate."))
      .finally(() => setLoading(false));
  }

  useEffect(load, [companyId]);

  async function handleReviewSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setSubmitMsg("");
    try {
      await apiClient.post(`/banker/mandates/${companyId}/review`, { status, comment });
      setSubmitMsg("Review saved.");
      load();
    } catch (err) {
      setSubmitMsg(err.response?.data?.detail || "Couldn't save the review.");
    } finally {
      setSubmitting(false);
    }
  }

  const gapsByPriority = { HIGH: [], MEDIUM: [], LOW: [] };
  detail?.gap_list.forEach((g) => gapsByPriority[g.priority]?.push(g));

  return (
    <div className="dash-page">
      <button type="button" className="btn-ghost" onClick={() => navigate("/banker/dashboard")}>
        ← Back to mandates
      </button>

      {loading && <p className="placeholder-note">Loading…</p>}
      {errorMsg && <p className="field-error">{errorMsg}</p>}

      {detail && (
        <>
          <div className="dash-header" style={{ marginTop: "1rem" }}>
            <div>
              <div className="pane-eyebrow">Merchant banker review</div>
              <h1 className="dash-title">{detail.company.name}</h1>
            </div>
          </div>

          <div className="mock-card" style={{ marginBottom: "1.5rem" }}>
            <span className={`status ${moduleStatusClass(detail.company.completeness_score, 100)}`}>
              {detail.company.completeness_score}/100
            </span>
            <h3>Overall readiness</h3>
            <p>
              {detail.gap_list.length} gap{detail.gap_list.length === 1 ? "" : "s"} outstanding ·{" "}
              {detail.company.sector || "sector not specified"} ·{" "}
              {detail.company.proposed_issue_size_cr ?? "—"} ₹ Cr proposed issue
            </p>
          </div>

          <div className="mock-grid" style={{ marginBottom: "1.5rem" }}>
            {detail.modules.map((m) => (
              <div className="mock-card" key={m.module}>
                <span className={`status ${moduleStatusClass(m.score, m.max)}`}>
                  {m.score}/{m.max}
                </span>
                <h3>{m.module}</h3>
                <p>{m.note}</p>
              </div>
            ))}
          </div>

          {detail.gap_list.length > 0 && (
            <div className="mock-card" style={{ marginBottom: "1.5rem" }}>
              <span className="status flag">
                {detail.gap_list.length} item{detail.gap_list.length === 1 ? "" : "s"} outstanding
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
                          <p style={{ margin: 0 }}>{renderInlineMarkdown(g.description)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null
              )}
            </div>
          )}

          <div className="mock-card" style={{ marginBottom: "1.5rem" }}>
            <h3>Drafted sections</h3>
            {detail.draft_sections.length === 0 ? (
              <p className="placeholder-note">No sections drafted yet.</p>
            ) : (
              detail.draft_sections.map((d) => (
                <details key={d.section_name} style={{ marginTop: "0.75rem" }}>
                  <summary style={{ cursor: "pointer", fontWeight: 500 }}>
                    {d.section_name} (v{d.version})
                    {d.schedule_vi_clause && <span className="clause-tag"> {d.schedule_vi_clause}</span>}
                  </summary>
                  <div style={{ marginTop: "0.5rem" }}>{renderInlineMarkdown(d.content || "")}</div>
                </details>
              ))
            )}
          </div>

          <form className="mock-card" onSubmit={handleReviewSubmit}>
            <h3>Leave a review</h3>
            <p style={{ marginBottom: "1rem" }}>
              Current status:{" "}
              <span className="status pending">{detail.company.review_status}</span>
            </p>

            <label className="auth-label" htmlFor="review-status">Decision</label>
            <select
              id="review-status"
              className="intake-input"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              style={{ marginBottom: "1rem" }}
            >
              <option value="reviewed">Reviewed — no decision yet</option>
              <option value="approved">Approved</option>
              <option value="changes_requested">Changes requested</option>
            </select>

            <label className="auth-label" htmlFor="review-comment">Comment (optional)</label>
            <textarea
              id="review-comment"
              className="intake-input"
              rows={4}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Notes for the promoter…"
              style={{ marginBottom: "1rem", resize: "vertical" }}
            />

            {submitMsg && <p className="field-error" style={{ marginBottom: "1rem" }}>{submitMsg}</p>}

            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? "Saving…" : "Submit review"}
            </button>
          </form>
        </>
      )}
    </div>
  );
}
