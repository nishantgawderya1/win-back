import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import { ProgressDots } from "../../components/common/index.jsx";
import { api } from "../../lib/api.js";

export default function Mode() {
  const { chooseMode } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState(null);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api
      .connection()
      .then((c) => setWebhookUrl(c.webhook_url))
      .catch(() => setWebhookUrl(`${window.location.origin}/api/webhook/razorpay`));
  }, []);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(webhookUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked — the URL is selectable on screen */
    }
  };

  const submit = () => {
    chooseMode(mode);
    navigate("/onboarding/done");
  };

  return (
    <>
      <ProgressDots total={3} current={2} />
      <h1 className="ob-title">How do you want to use WinBack?</h1>

      <div className="mode-grid">
        <button
          type="button"
          className={`mode-card ${mode === "webhook" ? "mode-selected" : ""}`}
          onClick={() => setMode("webhook")}
          aria-pressed={mode === "webhook"}
        >
          <span className="mode-tag mono">RECOMMENDED</span>
          <h2 className="mode-title">Real-time</h2>
          <p className="mode-body">
            Add one URL to Razorpay. Every failed payment triggers recovery automatically.
          </p>
          <code className="mode-code mono">{webhookUrl || "loading…"}</code>
        </button>

        <button
          type="button"
          className={`mode-card ${mode === "batch" ? "mode-selected" : ""}`}
          onClick={() => setMode("batch")}
          aria-pressed={mode === "batch"}
        >
          <h2 className="mode-title">Upload a file</h2>
          <p className="mode-body">
            Upload a CSV of failed payments. Process them in one batch and see results immediately.
          </p>
          <span className="mode-note mono dim">
            Good for running a demo or analysing past failures.
          </span>
        </button>
      </div>

      {mode === "webhook" && (
        <button type="button" className="linkish mono copy-row" onClick={copy}>
          {copied ? "copied ✓" : "copy webhook URL"}
        </button>
      )}

      <button
        type="button"
        className="btn btn-amber btn-block"
        disabled={!mode}
        onClick={submit}
      >
        Continue →
      </button>
    </>
  );
}
