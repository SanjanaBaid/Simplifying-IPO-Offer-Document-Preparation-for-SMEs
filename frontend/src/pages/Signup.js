import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const MODULES = [
  ["01", "Guided Intake — plain-language questionnaire, mapped 1:1 to Schedule VI"],
  ["02", "AI Draft — RAG-cited drafting from your intake answers"],
  ["03", "Consistency — narrative numbers checked against your financials"],
  ["04", "Risk Audit — boilerplate risk factors flagged before SEBI does"],
  ["05", "Scorecard & Handoff — a 100-point completeness package for your banker"],
];

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [firm, setFirm] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await signup({ fullName, email, password, merchantBankingFirm: firm });
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't create your account — try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-split-left">
        <div className="auth-split-left-inner">
          <div>
            <div className="auth-split-eyebrow">Sherpa · Drafting Copilot</div>
            <h1 className="auth-split-headline">Draft your first SME DRHP with Sherpa.</h1>
            <p className="auth-split-sub">
              Create an account to start a new mandate — guided intake, RAG-cited drafting,
              and a completeness scorecard, in one workspace.
            </p>
          </div>

          <div className="auth-split-modules">
            {MODULES.map(([num, label]) => (
              <div className="auth-split-module" key={num}>
                <span className="auth-split-module-num">{num}</span>
                <span>{label}</span>
              </div>
            ))}
          </div>

          <p className="auth-split-quote">"Sherpa drafts. The merchant banker still reviews, certifies, and files."</p>
        </div>
      </div>

      <div className="auth-split-right">
        <div className="auth-card">
          <div className="auth-brand">Sherpa</div>
          <p className="auth-tagline">Drafting copilot for SME DRHPs</p>

          <h1 className="auth-title">Create your account</h1>

          <form onSubmit={handleSubmit} className="auth-form">
            <label className="auth-label" htmlFor="fullName">Full name</label>
            <input
              id="fullName"
              type="text"
              className="intake-input"
              placeholder="Ankita Kumari"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />

            <label className="auth-label" htmlFor="firm">Merchant banking firm (optional)</label>
            <input
              id="firm"
              type="text"
              className="intake-input"
              placeholder="IIT Goa Merchant Advisory"
              value={firm}
              onChange={(e) => setFirm(e.target.value)}
            />

            <label className="auth-label" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              className="intake-input"
              placeholder="you@merchantbank.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

            <label className="auth-label" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              className="intake-input"
              placeholder="At least 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />

            {error && <p className="field-error">{error}</p>}

            <button type="submit" className="btn-primary auth-submit" disabled={submitting}>
              {submitting ? "Creating account…" : "Create account"}
            </button>
          </form>

          <p className="auth-switch">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}