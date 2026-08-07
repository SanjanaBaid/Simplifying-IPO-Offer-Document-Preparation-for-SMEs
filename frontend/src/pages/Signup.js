import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

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
  );
}