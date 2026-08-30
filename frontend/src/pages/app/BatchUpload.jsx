import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../../layouts/AppLayout.jsx";
import { api } from "../../lib/api.js";

// The columns backend/api/routes/batch.py:_row_to_state actually reads. Note
// there is no `failure_type` column — the agent derives that from the Razorpay
// error code, and prior_payments/prior_recoveries drive the recovery score.
const EXPECTED_COLUMNS =
  "payment_id, amount, customer_id, customer_name, customer_phone, customer_email, " +
  "razorpay_error_code, prior_payments, prior_recoveries, customer_opted_out, failed_at";

/** Minimal CSV split for the preview only — the backend does the real parse. */
function previewRows(text, limit = 5) {
  const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length === 0) return { headers: [], rows: [], total: 0 };
  const split = (line) => line.split(",").map((c) => c.trim());
  return {
    headers: split(lines[0]),
    rows: lines.slice(1, limit + 1).map(split),
    total: lines.length - 1,
  };
}

export default function BatchUpload() {
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const accept = async (f) => {
    if (!f) return;
    setError(null);
    setFile(f);
    try {
      setPreview(previewRows(await f.text()));
    } catch {
      setPreview(null);
    }
  };

  const run = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.uploadBatch(file);
      navigate(`/batch/${res.batch_id}`);
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader title="New batch" meta="upload a CSV of failed payments" />

      <div className="upload-wrap">
        <div
          className={`dropzone ${dragging ? "dropzone-over" : ""} ${file ? "dropzone-filled" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            accept(e.dataTransfer.files?.[0]);
          }}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        >
          <svg className="upload-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 17V4M12 4l-5 5M12 4l5 5M4 19h16" />
          </svg>
          {file ? (
            <p className="mono dropzone-file">{file.name}</p>
          ) : (
            <p className="dropzone-text">Drop your CSV here or click to browse</p>
          )}
          <p className="mono dim dropzone-cols">Expected columns: {EXPECTED_COLUMNS}</p>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            hidden
            onChange={(e) => accept(e.target.files?.[0])}
          />
        </div>

        {preview && (
          <section className="preview">
            <header className="preview-head mono dim">
              Preview — first {preview.rows.length} of {preview.total} rows
            </header>
            <div className="table-wrap">
              <table className="dt">
                <thead>
                  <tr>
                    {preview.headers.map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.map((row, i) => (
                    <tr key={i} className="dt-row">
                      {row.map((cell, j) => (
                        <td key={j} className="mono">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {error && <p className="error mono">{error}</p>}

        <button
          type="button"
          className="btn btn-primary btn-block"
          disabled={!file || busy}
          onClick={run}
        >
          {busy ? "Starting…" : "Run WinBack →"}
        </button>
      </div>
    </>
  );
}
