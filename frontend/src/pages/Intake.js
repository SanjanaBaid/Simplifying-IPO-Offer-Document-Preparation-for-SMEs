import PageShell from "../components/PageShell";

const FIELDS = [
  { status: "clear", title: "Promoter & company details", desc: "Legal name, CIN, registered office, incorporation date." },
  { status: "clear", title: "Business & operations", desc: "Nature of business, products, manufacturing locations." },
  { status: "pending", title: "Objects of the issue", desc: "Use of proceeds — plain-language answers, not yet mapped." },
  { status: "pending", title: "Promoter shareholding history", desc: "Allotments, transfers, and lock-in eligible holdings." },
  { status: "flag", title: "Related party transactions", desc: "2 answers conflict with the financials upload — needs review." },
  { status: "clear", title: "Risk factor inputs", desc: "Promoter-reported operational and industry risks." },
];

export default function Intake() {
  return (
    <PageShell
      eyebrow="Module 01 — Camp I"
      title="Guided Intake"
      sub="A plain-language questionnaire that maps every answer 1:1 to a Schedule VI data field, so promoters never see regulatory language directly."
    >
      <div className="mock-grid">
        {FIELDS.map((f) => (
          <div className="mock-card" key={f.title}>
            <span className={`status ${f.status}`}>
              {f.status === "clear" ? "Answered" : f.status === "pending" ? "In progress" : "Needs review"}
            </span>
            <h3>{f.title}</h3>
            <p>{f.desc}</p>
          </div>
        ))}
      </div>
      <p className="placeholder-note">
        Mock data — Step 5 wires this to POST /intake and the Schedule VI field mapping.
      </p>
    </PageShell>
  );
}
