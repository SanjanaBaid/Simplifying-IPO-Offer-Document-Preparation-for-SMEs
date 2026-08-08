import { NavLink, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const MODULES = [
  { path: "intake", label: "Guided intake" },
  { path: "drafting", label: "AI draft" },
  { path: "consistency", label: "Consistency" },
  { path: "audit", label: "Risk audit" },
  { path: "handoff", label: "Scorecard & handoff" },
];

export default function TopNav() {
  const { promoter, logout } = useAuth();
  const { companyId } = useParams();
  const navigate = useNavigate();

  async function handleSignOut() {
    await logout();
    navigate("/login");
  }

  return (
    <header className="top-nav">
      <div className="top-nav-row">
        <NavLink to={promoter?.role === "banker" ? "/banker/dashboard" : "/dashboard"} className="top-nav-brand">
          <span className="mark">Sherpa</span>
          <span className="tag">Drafting copilot · SME DRHP</span>
        </NavLink>

        {promoter && (
          <div className="top-nav-user">
            <div className="top-nav-user-info">
              <span className="top-nav-user-name">
                {promoter.full_name}
                {promoter.role === "banker" && <span className="top-nav-role-badge">Banker</span>}
              </span>
              {promoter.merchant_banking_firm && (
                <span className="top-nav-user-firm">{promoter.merchant_banking_firm}</span>
              )}
            </div>
            <button type="button" className="btn-ghost top-nav-signout" onClick={handleSignOut}>
              Sign out
            </button>
          </div>
        )}
      </div>

      {promoter?.role === "promoter" && companyId && (
        <nav className="top-nav-tabs">
          {MODULES.map((m) => (
            <NavLink
              key={m.path}
              to={`/company/${companyId}/${m.path}`}
              className={({ isActive }) => `top-nav-tab ${isActive ? "active" : ""}`}
            >
              {m.label}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  );
}