import { useCallback, useEffect, useRef, useState } from "react";
import apiClient from "../api/client";

const ACCEPTED_TYPE = "application/pdf";

export default function FinancialUpload({ companyId }) {
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | uploading | success | error
  const [errorMsg, setErrorMsg] = useState("");
  const [result, setResult] = useState(null); // { filename, line_items }
  const inputRef = useRef(null);

  useEffect(() => {
    if (!companyId) return;
    let cancelled = false;

    apiClient
      .get("/financials", { params: { company_id: companyId } })
      .then(({ data }) => {
        if (cancelled || !data.document_id) return;
        setResult({ filename: data.filename, line_items: data.line_items });
        setStatus("success");
      })
      .catch(() => {
        // No prior upload, or the fetch failed — leave the dropzone as-is.
      });

    return () => {
      cancelled = true;
    };
  }, [companyId]);

  const uploadFile = useCallback(
    async (file) => {
      if (!companyId) {
        setStatus("error");
        setErrorMsg("Enter a company ID above before uploading a financial document.");
        return;
      }
      if (file.type && file.type !== ACCEPTED_TYPE) {
        setStatus("error");
        setErrorMsg("Only PDF financials are supported right now.");
        return;
      }

      const form = new FormData();
      form.append("company_id", companyId);
      form.append("file", file);

      setStatus("uploading");
      setErrorMsg("");
      setResult(null);
      try {
        const { data } = await apiClient.post("/upload-financials", form, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        setResult(data);
        setStatus("success");
      } catch (err) {
        setStatus("error");
        setErrorMsg(
          err.response?.data?.detail ||
            "Upload failed — confirm the backend is running and reachable."
        );
      }
    },
    [companyId]
  );

  function handleDrop(e) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) uploadFile(file);
  }

  function handleBrowse(e) {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
    e.target.value = ""; // allow re-uploading the same filename
  }

  return (
    <div className="financial-upload">
      <h3 className="upload-title">Upload financial statements</h3>
      <p className="upload-sub">
        Drop a PDF financial statement to extract line items — they'll be saved against
        this company's record.
      </p>

      <div
        className={`dropzone ${isDragging ? "dragging" : ""} ${
          status === "uploading" ? "busy" : ""
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="dropzone-input"
          onChange={handleBrowse}
        />
        {status === "uploading" ? (
          <p>Extracting line items…</p>
        ) : (
          <p>
            Drag a PDF here, or <span className="dropzone-link">browse</span>
          </p>
        )}
      </div>

      {status === "error" && <p className="field-error">{errorMsg}</p>}

      {status === "success" && result && (
        <div className="mock-card upload-result">
          <span className="status clear">Extracted</span>
          <h3>{result.filename}</h3>
          {result.line_items?.length ? (
            <table className="line-items-table">
              <thead>
                <tr>
                  <th>Label</th>
                  <th>Period</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {result.line_items.map((item, i) => (
                  <tr key={i}>
                    <td>{item.label}</td>
                    <td>{item.period || "—"}</td>
                    <td>{item.value ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>No line items were detected in this document.</p>
          )}
        </div>
      )}
    </div>
  );
}