import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";

export default function Dashboard() {
  const navigate = useNavigate();
  const [mandates, setMandates] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [sector, setSector] = useState("");
  const [issueSize, setIssueSize] = useState("");
  const [contactName, setContactName] = useState("");
  const [creating, setCreating] = useState(false);

  async function loadMandates() {
    setLoading(true);
    setErrorMsg("");
    try {
      const { data } = await apiClient.get("/companies");
      setMandates(data);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || "Couldn't load your mandates.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMandates();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setCreating(true);
    setErrorMsg("");
    try {
      const { data } = await apiClient.post("/companies", {
        name,
        sector: sector || null,
        proposed_issue_size_cr: issueSize ? Number(issueSize) : null,
        promoter_contact_name: contactName || null,
      });
      navigate(`/company/${data.id}/intake`);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || "Couldn't create the mandate.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="dash-page">
      <div className="dash-header">
        <div>
          <div className="pane-eyebrow">Merchant banker dashboard</div>
          <h1 className="dash-title">Active SME mandates</h1>
        </div>
        <button type="button" className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "+ New mandate"}
        </button>
      </div>

      {showForm && (
        <form className="mandate-form" onSubmit={handleCreate}>
          <div className="mandate-form-grid">
            <div>
              <label className="auth-label" htmlFor="m-name">Issuer name</label>
              <input
                id="m-name"
                className="intake-input"
                placeholder="Aravalli Precision Components Limited"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="auth-label" htmlFor="m-sector">Sector</label>
              <input
                id="m-sector"
                className="intake-input"
                placeholder="Auto components"
                value={sector}
                onChange={(e) => setSector(e.target.value)}
              />
            </div>
            <div>
              <label className="auth-label" htmlFor="m-issue">Proposed issue size (₹ Cr)</label>
              <input
                id="m-issue"
                type="number"
                className="intake-input"
                placeholder="31"
                value={issueSize}
                onChange={(e) => setIssueSize(e.target.value)}
              />
            </div>
            <div>
              <label className="auth-label" htmlFor="m-contact">Promoter contact name</label>
              <input
                id="m-contact"
                className="intake-input"
                placeholder="Ashwin Kulkarni"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
              />
            </div>
          </div>
          <button type="submit" className="btn-primary" disabled={creating}>
            {creating ? "Creating…" : "Create mandate"}
          </button>
        </form>
      )}

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
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => navigate(`/company/${m.id}/intake`)}
                  >
                    Open →
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="placeholder-note">
          No mandates yet — click "+ New mandate" to start your first SME DRHP draft.
        </p>
      )}
    </div>
  );
}