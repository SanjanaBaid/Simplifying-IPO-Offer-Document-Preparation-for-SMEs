import PageShell from "../components/PageShell";

const SECTIONS = [
  { status: "clear", title: "Cover page & definitions", desc: "Drafted from intake + Schedule VI templates." },
  { status: "clear", title: "Industry & business overview", desc: "Drafted, pending promoter sign-off." },
  { status: "pending", title: "Financial statements section", desc: "Waiting on extracted line items from uploaded PDFs." },
  { status: "pending", title: "Management discussion & analysis", desc: "Draft in progress — 3 of 8 sub-clauses generated." },
  { status: "clear", title: "Risk factors", desc: "Drafted from promoter-reported risks, ICDR-clause tagged." },
  { status: "flag", title: "Legal & regulatory disclosures", desc: "Missing one required SME Chapter IX disclosure." },
];

export default function Drafting() {
  return (
    <PageShell
      eyebrow="Module 02 — Camp II"
      title="Drafting Engine"
      sub="Assembles offer document sections from intake answers and extracted financials, each clause traceable back to its ICDR Schedule VI source."
    >
      <div className="mock-grid">
        {SECTIONS.map((s) => (
          <div className="mock-card" key={s.title}>
            <span className={`status ${s.status}`}>
              {s.status === "clear" ? "Drafted" : s.status === "pending" ? "In progress" : "Incomplete"}
            </span>
            <h3>{s.title}</h3>
            <p>{s.desc}</p>
          </div>
        ))}
      </div>
      <p className="placeholder-note">
        Mock data — later steps connect this to the Draft Sections schema and clause-level ChromaDB retrieval.
      </p>
    </PageShell>
  );
}
