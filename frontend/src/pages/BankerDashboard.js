import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";

const REVIEW_LABELS = {
  not_reviewed: "Not reviewed",
  reviewed: "Reviewed",
  approved: "Approved",
  changes_requested: "Changes requested",
};

const REVIEW_CLASS = {
  not_reviewed: "pending",
  reviewed: "pending",
  approved: "clear",
  changes_requested: "flag",
};

export default function BankerDashboard() {
  const navigate = useNavigate();
  const [mandates, setMandates] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    apiClient
      .get("/banker/mandates")
      .then(({ data }) => setMandates(data))
      .catch((err) => setErrorMsg(err.response?.data?.detail || "Couldn't load your mandates."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="dash-page">
      <div className="dash-header">
        <div>
          <div className="pane-eyebrow">Merchant banker workspace</div>
          <h1 className="dash-title">Mandates shared with you</h1>
        </div>
      </div>

      {errorMsg && <p className="field-error">{errorMsg}</p>}

      {loading ? (
        <p className="placeholder-note">Loading mandates…</p>
      ) : mandates && mandates.length > 0 ? (
        <table className="mandate-table">
          <thead>
            <tr>
              <th>Issuer</th>
              <th>Sector</th>
              <th>Issue size (₹ Cr)</th>
              <th>Completeness</th>
              <th>Review status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {mandates.map((m) => (
              <tr key={m.id}>
                <td>
                  <div className="mandate-name">{m.name}</div>
                  {m.promoter_contact_name && (
                    <div className="mandate-contact">{m.promoter_contact_name}</div>
                  )}
                </td>
                <td>{m.sector || "—"}</td>
                <td>{m.proposed_issue_size_cr ?? "—"}</td>
                <td>
                  <span className="mandate-score">{m.completeness_score}</span>
                  <span className="mandate-score-max">/100</span>
                </td>
                <td>
                  <span className={`status ${REVIEW_CLASS[m.review_status] || "pending"}`}>
                    {REVIEW_LABELS[m.review_status] || m.review_status}
                  </span>
                </td>
                <td>
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => navigate(`/banker/mandates/${m.id}`)}
                  >
                    Review →
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="placeholder-note">
          No mandates have been shared with you yet. Ask a promoter to share a mandate with your
          account email from their Handoff page.
        </p>
      )}
    </div>
  );
}
