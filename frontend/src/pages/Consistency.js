import PageShell from "../components/PageShell";

const CHECKS = [
  { status: "clear", title: "Revenue figures", desc: "Matches across MD&A, financials, and summary tables." },
  { status: "flag", title: "Promoter shareholding %", desc: "12.4% in intake vs. 12.9% in the capital structure section." },
  { status: "clear", title: "Registered office address", desc: "Consistent across cover page, definitions, and annexures." },
  { status: "flag", title: "Objects of the issue amount", desc: "₹ figure in cover page doesn't sum to the use-of-proceeds table." },
  { status: "clear", title: "Related party names", desc: "Consistent between disclosures and financial statement notes." },
];

export default function Consistency() {
  return (
    <PageShell
      eyebrow="Module 03 — Camp III"
      title="Consistency Checker"
      sub="Cross-references figures, names, and dates across every drafted section, flagging mismatches before they reach the auditor."
    >
      <div className="mock-grid">
        {CHECKS.map((c) => (
          <div className="mock-card" key={c.title}>
            <span className={`status ${c.status}`}>{c.status === "clear" ? "Consistent" : "Mismatch"}</span>
            <h3>{c.title}</h3>
            <p>{c.desc}</p>
          </div>
        ))}
      </div>
      <p className="placeholder-note">
        Mock data — real checks will diff extracted financial line items against drafted section text.
      </p>
    </PageShell>
  );
}
