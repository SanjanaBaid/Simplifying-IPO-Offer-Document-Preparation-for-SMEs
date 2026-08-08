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

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const loggedInPromoter = await login({ email, password });
      navigate(loggedInPromoter.role === "banker" ? "/banker/dashboard" : "/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't sign in — check your email and password.");
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
            <h1 className="auth-split-headline">Welcome back to your DRHP workspace.</h1>
            <p className="auth-split-sub">
              Sign in to pick up where you left off — your mandates, drafts, and completeness
              scores are all right where you left them.
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

          <h1 className="auth-title">Sign in</h1>

          <form onSubmit={handleSubmit} className="auth-form">
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
              placeholder="Your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            {error && <p className="field-error">{error}</p>}

            <button type="submit" className="btn-primary auth-submit" disabled={submitting}>
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <p className="auth-switch">
            New here? <Link to="/signup">Create an account</Link>
          </p>
        </div>
      </div>
    </div>
  );
}