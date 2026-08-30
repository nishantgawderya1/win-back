import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import { ProgressDots } from "../../components/common/index.jsx";

export default function Connect() {
  const { connectRazorpay } = useAuth();
  const navigate = useNavigate();
  const [keyId, setKeyId] = useState("");
  const [secret, setSecret] = useState("");
  const [reveal, setReveal] = useState(false);

  const submit = (e) => {
    e.preventDefault();
    // Only the key id is retained. The secret is deliberately dropped here —
    // see the note in AuthContext. Nothing downstream needs it.
    connectRazorpay(keyId);
    navigate("/onboarding/mode");
  };

  return (
    <>
      <ProgressDots total={3} current={1} />
      <h1 className="ob-title">Connect your Razorpay account</h1>
      <p className="ob-sub">
        Paste your test-mode API keys. WinBack only reads payment events. It never writes to your
        account without an explicit action.
      </p>

      <form onSubmit={submit} className="ob-form">
        <label className="field">
          <span className="field-label mono">KEY ID</span>
          <input
            className="mono"
            required
            value={keyId}
            onChange={(e) => setKeyId(e.target.value)}
            placeholder="rzp_test_xxxxxxxxxxxx"
          />
        </label>

        <label className="field">
          <span className="field-label mono">
            KEY SECRET
            <button type="button" className="linkish mono" onClick={() => setReveal((r) => !r)}>
              {reveal ? "hide" : "reveal"}
            </button>
          </span>
          <input
            className="mono"
            required
            type={reveal ? "text" : "password"}
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            placeholder="••••••••••••••••"
          />
        </label>

        <div className="callout">
          <p>
            WinBack uses test-mode only. All payment operations carry idempotency keys. No real
            money moves without your configuration.
          </p>
          <p className="mono dim">
            This is a demo build: the secret is not transmitted or stored anywhere — only the
            masked key id is kept, in this browser.
          </p>
        </div>

        <button type="submit" className="btn btn-amber btn-block">
          Connect →
        </button>
      </form>

      <p className="ob-hint mono dim">
        <a
          href="https://dashboard.razorpay.com/app/keys"
          target="_blank"
          rel="noreferrer noopener"
        >
          dashboard.razorpay.com → Settings → API Keys → Generate Test Key
        </a>
      </p>
    </>
  );
}
