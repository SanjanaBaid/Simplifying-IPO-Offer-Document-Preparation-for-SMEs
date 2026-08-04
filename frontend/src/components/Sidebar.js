import { NavLink, useLocation } from "react-router-dom";

// Each module is framed as a camp along the drafting route — altitude
// stands in for how far a promoter has climbed toward a filed offer document.
const CAMPS = [
  { path: "/intake", alt: "Camp I", name: "Intake", icon: "01" },
  { path: "/drafting", alt: "Camp II", name: "Drafting", icon: "02" },
  { path: "/consistency", alt: "Camp III", name: "Consistency", icon: "03" },
  { path: "/audit", alt: "Camp IV", name: "Audit", icon: "04" },
  { path: "/handoff", alt: "Summit", name: "Handoff", icon: "05" },
];

export default function Sidebar() {
  const location = useLocation();
  const activeIndex = CAMPS.findIndex((c) => c.path === location.pathname);

  return (
    <nav className="route-rail">
      <div className="rail-brand">
        <span className="mark">Sherpa</span>
        <span className="tag">SME IPO</span>
      </div>

      <div className="trail">
        <div className="trail-line" />
        {CAMPS.map((camp, i) => {
          const isActive = i === activeIndex;
          const isDone = activeIndex >= 0 && i < activeIndex;
          return (
            <NavLink
              key={camp.path}
              to={camp.path}
              className={`camp ${isActive ? "active" : ""} ${isDone ? "done" : ""}`}
            >
              <span className="camp-marker">{isDone ? "✓" : camp.icon}</span>
              <span className="camp-label">
                <span className="camp-alt">{camp.alt}</span>
                <span className="camp-name">{camp.name}</span>
              </span>
            </NavLink>
          );
        })}
      </div>

      <div className="rail-footer">
        SEBI ICDR · Schedule VI
        <br />
        Regulation 229 — SME Chapter IX
      </div>
    </nav>
  );
}
