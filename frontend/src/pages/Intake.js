import { useMemo, useState } from "react";
import PageShell from "../components/PageShell";
import { SECTIONS, ALL_FIELDS } from "../scheduleViFields";

// Guided Intake — Step 4.
//
// Renders the Schedule VI field catalogue as a plain-language questionnaire,
// one section ("camp leg") at a time. Every question maps 1:1 to a
// ScheduleVIField row via field_key, and validation mirrors the Pydantic
// validators Person A will wire up server-side in Step 5.
//
// This step is intentionally not connected to the API yet — that's Step 6
// (axios wiring to POST /intake). The "Review & submit" screen instead shows
// exactly the payload shape that call will send, so both sides can confirm
// the contract before the wire-up.

function fieldError(field, value) {
  if (field.optional && (value === undefined || value === "" || value === null)) {
    return null;
  }
  return field.validate ? field.validate(value) : null;
}

function FieldInput({ field, value, error, onChange }) {
  const commonProps = {
    id: field.field_key,
    value: value ?? "",
    onChange: (e) => onChange(field.field_key, e.target.value),
    className: `intake-input ${error ? "has-error" : ""}`,
    placeholder: field.placeholder,
  };

  return (
    <div className="intake-field">
      <label htmlFor={field.field_key}>
        <span className="clause-tag">{field.clause_number}</span>
        <span className="prompt-text">
          {field.plain_language_prompt}
          {field.optional && <span className="optional-tag"> (optional)</span>}
        </span>
      </label>
      {field.helper && <p className="field-helper">{field.helper}</p>}

      {field.field_type === "textarea" && <textarea rows={4} {...commonProps} />}

      {field.field_type === "select" && (
        <select {...commonProps}>
          {field.options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      )}

      {field.field_type === "number" && <input type="number" {...commonProps} />}

      {field.field_type === "date" && <input type="date" {...commonProps} />}

      {(field.field_type === "text" || !field.field_type) && (
        <input type="text" {...commonProps} />
      )}

      {error && <p className="field-error">{error}</p>}
    </div>
  );
}

export default function Intake() {
  const [values, setValues] = useState({});
  const [touched, setTouched] = useState({});
  const [step, setStep] = useState(0); // index into SECTIONS, SECTIONS.length === review screen
  const [submitted, setSubmitted] = useState(false);

  const isReview = step === SECTIONS.length;
  const currentSection = SECTIONS[step];

  const errors = useMemo(() => {
    const e = {};
    for (const f of ALL_FIELDS) {
      const err = fieldError(f, values[f.field_key]);
      if (err) e[f.field_key] = err;
    }
    return e;
  }, [values]);

  const sectionHasErrors = (section) =>
    section.fields.some((f) => touched[f.field_key] && errors[f.field_key]);

  const sectionIsComplete = (section) =>
    section.fields.every((f) => !fieldError(f, values[f.field_key]));

  function handleChange(fieldKey, val) {
    setValues((prev) => ({ ...prev, [fieldKey]: val }));
    setTouched((prev) => ({ ...prev, [fieldKey]: true }));
  }

  function touchSection(section) {
    setTouched((prev) => {
      const next = { ...prev };
      section.fields.forEach((f) => (next[f.field_key] = true));
      return next;
    });
  }

  function goNext() {
    if (!isReview) {
      touchSection(currentSection);
      if (!sectionIsComplete(currentSection)) return;
    }
    setStep((s) => Math.min(s + 1, SECTIONS.length));
  }

  function goBack() {
    setStep((s) => Math.max(s - 1, 0));
  }

  function goToSection(i) {
    setStep(i);
  }

  const overallComplete = ALL_FIELDS.every((f) => !fieldError(f, values[f.field_key]));

  // Shape of the POST /intake payload Step 5/6 will send — a list of
  // { field_key, response_text } pairs the backend maps to IntakeSession rows.
  const payloadPreview = ALL_FIELDS.map((f) => ({
    field_key: f.field_key,
    clause_number: f.clause_number,
    response_text: values[f.field_key] ?? "",
  }));

  function handleSubmit() {
    ALL_FIELDS.forEach((f) => (touched[f.field_key] = true));
    setTouched({ ...touched });
    if (!overallComplete) return;
    setSubmitted(true);
    // Step 6 will replace this with:
    //   axios.post("/intake", { company_id, responses: payloadPreview })
    console.log("Intake payload (mock — wired in Step 6):", payloadPreview);
  }

  const answeredCount = ALL_FIELDS.filter((f) => !fieldError(f, values[f.field_key])).length;

  return (
    <PageShell
      eyebrow="Module 01 — Camp I"
      title="Guided Intake"
      sub="A plain-language questionnaire that maps every answer 1:1 to a Schedule VI data field, so promoters never see regulatory language directly."
    >
      <div className="intake-progress">
        {SECTIONS.map((s, i) => (
          <button
            type="button"
            key={s.section_key}
            className={`progress-pip ${i === step ? "active" : ""} ${
              sectionIsComplete(s) ? "complete" : ""
            } ${sectionHasErrors(s) ? "flagged" : ""}`}
            onClick={() => goToSection(i)}
          >
            <span className="pip-index">{String(i + 1).padStart(2, "0")}</span>
            <span className="pip-name">{s.section_name}</span>
          </button>
        ))}
        <button
          type="button"
          className={`progress-pip ${isReview ? "active" : ""}`}
          onClick={() => goToSection(SECTIONS.length)}
        >
          <span className="pip-index">✓</span>
          <span className="pip-name">Review & submit</span>
        </button>
      </div>

      <div className="intake-progress-meta">
        {answeredCount} of {ALL_FIELDS.length} fields answered
      </div>

      {!isReview && (
        <div className="intake-section">
          <h2 className="intake-section-title">{currentSection.section_name}</h2>
          <p className="intake-section-intro">{currentSection.intro}</p>

          {currentSection.fields.map((f) => (
            <FieldInput
              key={f.field_key}
              field={f}
              value={values[f.field_key]}
              error={touched[f.field_key] ? errors[f.field_key] : null}
              onChange={handleChange}
            />
          ))}

          <div className="intake-nav">
            <button type="button" className="btn-ghost" onClick={goBack} disabled={step === 0}>
              Back
            </button>
            <button type="button" className="btn-primary" onClick={goNext}>
              {step === SECTIONS.length - 1 ? "Review answers" : "Next section"}
            </button>
          </div>
        </div>
      )}

      {isReview && !submitted && (
        <div className="intake-section">
          <h2 className="intake-section-title">Review & submit</h2>
          <p className="intake-section-intro">
            {overallComplete
              ? "Every field validates cleanly. Submitting will map these answers to their Schedule VI clauses."
              : "Some fields still need attention — jump back into a section above to fix them."}
          </p>

          <div className="review-grid">
            {SECTIONS.map((s) => (
              <div className="review-card" key={s.section_key}>
                <div className="review-card-head">
                  <h3>{s.section_name}</h3>
                  <span className={`status ${sectionIsComplete(s) ? "clear" : "flag"}`}>
                    {sectionIsComplete(s) ? "Complete" : "Incomplete"}
                  </span>
                </div>
                {s.fields.map((f) => (
                  <div className="review-row" key={f.field_key}>
                    <span className="review-clause">{f.clause_number}</span>
                    <span className="review-value">
                      {values[f.field_key] ? String(values[f.field_key]) : "—"}
                    </span>
                  </div>
                ))}
              </div>
            ))}
          </div>

          <div className="intake-nav">
            <button type="button" className="btn-ghost" onClick={goBack}>
              Back
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={handleSubmit}
              disabled={!overallComplete}
            >
              Submit intake
            </button>
          </div>
        </div>
      )}

      {submitted && (
        <div className="intake-section">
          <div className="mock-card submitted-card">
            <span className="status clear">Saved locally</span>
            <h3>Intake captured</h3>
            <p>
              All {ALL_FIELDS.length} answers validated and are mapped to their Schedule VI
              field keys below. Step 5 adds <code>POST /intake</code>, and Step 6 swaps the
              button above for a real <code>axios</code> call — no changes needed here.
            </p>
          </div>
          <pre className="payload-preview">{JSON.stringify(payloadPreview, null, 2)}</pre>
          <div className="intake-nav">
            <button type="button" className="btn-ghost" onClick={() => setSubmitted(false)}>
              Back to review
            </button>
          </div>
        </div>
      )}
    </PageShell>
  );
}
