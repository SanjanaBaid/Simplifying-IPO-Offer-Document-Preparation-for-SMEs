import PageShell from "../components/PageShell";

const PACKAGE_ITEMS = [
  { status: "clear", title: "Consolidated draft offer document", desc: "All sections merged, clause-tagged, ready for review." },
  { status: "clear", title: "Consistency check report", desc: "2 resolved flags, 0 outstanding mismatches." },
  { status: "flag", title: "Audit findings summary", desc: "2 unresolved gaps included — banker sign-off required." },
  { status: "clear", title: "Financial data room", desc: "Extracted line items with source PDF references." },
];

export default function Handoff() {
  return (
    <PageShell
      eyebrow="Module 05 — Summit"
      title="Merchant Banker Handoff"
      sub="Packages the audited draft, consistency report, and supporting financial data into a single review-ready bundle for the merchant banker."
    >
      <div className="mock-grid">
        {PACKAGE_ITEMS.map((p) => (
          <div className="mock-card" key={p.title}>
            <span className={`status ${p.status}`}>{p.status === "clear" ? "Ready" : "Needs sign-off"}</span>
            <h3>{p.title}</h3>
            <p>{p.desc}</p>
          </div>
        ))}
      </div>
      <p className="placeholder-note">
        Mock data — later steps generate a downloadable package and a banker-facing review link.
      </p>
    </PageShell>
  );
}
