import PageShell from "../components/PageShell";

const FINDINGS = [
  { status: "clear", title: "Schedule VI clause coverage", desc: "58 of 58 required clauses have drafted content." },
  { status: "flag", title: "Missing statutory disclosure", desc: "Regulation 229(4) litigation disclosure not yet addressed." },
  { status: "pending", title: "Risk factor completeness", desc: "Industry risks covered; financial risks section thin." },
  { status: "clear", title: "Financial statement annexures", desc: "All required schedules attached and cross-tagged." },
  { status: "flag", title: "Promoter lock-in computation", desc: "Computed lock-in % falls below the SME minimum threshold." },
];

export default function Audit() {
  return (
    <PageShell
      eyebrow="Module 04 — Camp IV"
      title="Risk & Completeness Auditor"
      sub="Runs the near-final draft against ICDR Schedule VI and SME Chapter IX requirements, surfacing gaps before merchant banker review."
    >
      <div className="mock-grid">
        {FINDINGS.map((f) => (
          <div className="mock-card" key={f.title}>
            <span className={`status ${f.status}`}>
              {f.status === "clear" ? "Satisfied" : f.status === "pending" ? "Partial" : "Gap found"}
            </span>
            <h3>{f.title}</h3>
            <p>{f.desc}</p>
          </div>
        ))}
      </div>
      <p className="placeholder-note">
        Mock data — real findings will cite the specific ICDR clause number and drafted paragraph.
      </p>
    </PageShell>
  );
}
