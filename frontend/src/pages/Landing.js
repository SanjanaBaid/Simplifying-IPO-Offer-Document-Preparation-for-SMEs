import { Navigate, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const HANDOFF_PACKAGE = [
  "Section-by-section DRHP draft, cited to Schedule VI",
  "100-point completeness scorecard with per-module breakdown",
  "Prioritised gap list — HIGH / MEDIUM / LOW",
  "Boilerplate risk-factor flags, with reasoning",
  "Narrative-vs-financials variance report",
  "Exportable handoff package — JSON or PDF",
];

const MODULES = [
  ["01", "Guided Intake", "Plain-language questionnaire, mapped 1:1 to Schedule VI data fields."],
  ["02", "AI Draft", "RAG-cited drafting from your intake answers and the embedded SEBI knowledge base."],
  ["03", "Consistency", "Narrative numbers cross-checked against your uploaded financial statements."],
  ["04", "Risk Audit", "Boilerplate risk factors flagged before your merchant banker — or SEBI — does."],
  ["05", "Scorecard & Handoff", "A 100-point completeness score and an exportable handoff package."],
];

export default function Landing() {
  const { token, loading } = useAuth();
  const navigate = useNavigate();

  if (!loading && token) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="landing">
      <header className="top-nav">
        <div className="top-nav-row">
          <div className="top-nav-brand">
            <span className="mark">Sherpa</span>
            <span className="tag">Drafting copilot · SME DRHP</span>
          </div>
          <NavLink to="/login" className="btn-ghost landing-nav-signin">
            Sign in
          </NavLink>
        </div>
      </header>

      <section className="landing-hero">
        <div className="landing-hero-left">
          <div className="pane-eyebrow">SME IPO drafting, simplified</div>
          <h1 className="landing-headline">
            Sherpa drafts. <em>The merchant banker still reviews, certifies, and files.</em>
          </h1>
          <p className="landing-sub">
            A RAG-powered drafting copilot that turns a guided promoter intake into a
            cited, auditable SEBI ICDR / Schedule VI–compliant offer document — and
            catches boilerplate risk factors and narrative-vs-financials mismatches
            before they reach your reviewer.
          </p>
          <button type="button" className="btn-primary landing-cta" onClick={() => navigate("/login")}>
            Enter Sherpa →
          </button>
        </div>

        <div className="landing-hero-right">
          <div className="landing-panel-eyebrow">Handoff package</div>
          <ul className="landing-panel-list">
            {HANDOFF_PACKAGE.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="landing-modules">
        <div className="pane-eyebrow" style={{ padding: "0 clamp(24px, 5vw, 64px)" }}>
          How it works
        </div>
        <div className="landing-modules-grid">
          {MODULES.map(([num, name, desc]) => (
            <div className="landing-module-card" key={num}>
              <span className="landing-module-num">{num}</span>
              <h3>{name}</h3>
              <p>{desc}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="landing-footer">
        <span className="top-nav-brand mark" style={{ fontSize: "16px" }}>Sherpa</span>
        <span>Built for SME issuers and their merchant bankers.</span>
      </footer>
    </div>
  );
}