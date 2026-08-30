import { useEffect, useState } from "react";
import { PageHeader } from "../../layouts/AppLayout.jsx";
import { Panel } from "../../components/common/index.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { api } from "../../lib/api.js";
import { dateTime } from "../../lib/format.js";

const RULE_FIELDS = [
  {
    key: "max_retry_attempts",
    label: "Max retry attempts",
    min: 1,
    max: 10,
    help: "Once a payment has been attempted this many times, the planner halts it instead of retrying.",
  },
  {
    key: "min_cooldown_minutes",
    label: "Cooldown between outreach (minutes)",
    min: 0,
    max: 1440,
    help: "A payment contacted more recently than this is halted rather than contacted again.",
  },
  {
    key: "outreach_cutoff_hour",
    label: "Outreach cutoff hour (0–23)",
    min: 0,
    max: 23,
    help: "No outreach is sent at or after this hour. Evaluated against server time (UTC).",
  },
  {
    key: "high_value_threshold_inr",
    label: "High-value threshold (₹)",
    min: 0,
    max: 10000000,
    help: "Payments above this amount are escalated for human approval instead of retried.",
  },
];

export default function Settings() {
  const { session } = useAuth();
  const [rules, setRules] = useState(null);
  const [draft, setDraft] = useState(null);
  const [conn, setConn] = useState(null);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api
      .getRules()
      .then((r) => {
        setRules(r);
        setDraft(r);
      })
      .catch(() => setStatus({ kind: "error", text: "Could not load stopping rules." }));
    api.connection().then(setConn).catch(() => setConn(null));
  }, []);

  const dirty =
    draft &&
    rules &&
    RULE_FIELDS.some((f) => Number(draft[f.key]) !== Number(rules[f.key]));

  const save = async () => {
    setSaving(true);
    setStatus(null);
    try {
      const saved = await api.saveRules({
        max_retry_attempts: Number(draft.max_retry_attempts),
        min_cooldown_minutes: Number(draft.min_cooldown_minutes),
        outreach_cutoff_hour: Number(draft.outreach_cutoff_hour),
        high_value_threshold_inr: Number(draft.high_value_threshold_inr),
      });
      setRules(saved);
      setDraft(saved);
      setStatus({ kind: "ok", text: "Rules saved. They apply from the next payment onward." });
    } catch (e) {
      setStatus({ kind: "error", text: `Save failed. ${e.message}` });
    } finally {
      setSaving(false);
    }
  };

  const copyWebhook = async () => {
    try {
      await navigator.clipboard.writeText(conn.webhook_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked — the URL is selectable on screen */
    }
  };

  return (
    <>
      <PageHeader
        title="Settings"
        meta={
          rules?.updated_at
            ? `rules last saved ${dateTime(rules.updated_at)}`
            : "rules currently at .env defaults"
        }
      />

      <Panel title="Stopping rules">
        <p className="settings-desc">
          These rules control when the agent stops acting. All of them are applied before any
          intervention is executed.
        </p>

        {!draft && <p className="empty muted">Loading…</p>}

        {draft &&
          RULE_FIELDS.map((f) => (
            <div className="rule-row" key={f.key}>
              <label className="rule-label" htmlFor={f.key}>
                {f.label}
              </label>
              <input
                id={f.key}
                className="mono rule-input"
                type="number"
                min={f.min}
                max={f.max}
                value={draft[f.key]}
                onChange={(e) => setDraft({ ...draft, [f.key]: e.target.value })}
              />
              <p className="rule-help">{f.help}</p>
            </div>
          ))}

        {status && (
          <p className={status.kind === "ok" ? "ok mono" : "error mono"}>{status.text}</p>
        )}

        <div className="settings-actions">
          <button
            type="button"
            className="btn btn-amber"
            onClick={save}
            disabled={!dirty || saving}
          >
            {saving ? "Saving…" : "Save rules"}
          </button>
        </div>
      </Panel>

      <Panel title="Razorpay connection">
        <div className="expand">
          <div className="expand-row">
            <span className="expand-key mono dim">key id</span>
            <span className="mono">
              {session?.keyIdMasked || conn?.razorpay_key_id_masked || "not connected"}
            </span>
          </div>
          <div className="expand-row">
            <span className="expand-key mono dim">mode</span>
            <span className="mono">{conn?.test_mode ? "TEST" : "LIVE"}</span>
          </div>
          <div className="expand-row">
            <span className="expand-key mono dim">webhook url</span>
            <span className="mono webhook-url">
              {conn?.webhook_url || "—"}
              {conn?.webhook_url && (
                <button className="linkish mono" onClick={copyWebhook}>
                  {copied ? "copied ✓" : "copy"}
                </button>
              )}
            </span>
          </div>
          <div className="expand-row">
            <span className="expand-key mono dim">diagnosis model</span>
            <span className="mono">{conn?.llm_model || "—"}</span>
          </div>
          <div className="expand-row">
            <span className="expand-key mono dim">model key</span>
            <span className={`mono ${conn?.llm_key_configured ? "" : "amber"}`}>
              {conn?.llm_key_configured
                ? "configured"
                : "not configured — diagnosis falls back to rules"}
            </span>
          </div>
        </div>
        <p className="settings-desc">
          Add the webhook URL in your Razorpay dashboard under Settings → Webhooks, subscribed to{" "}
          <span className="mono">payment.failed</span> and{" "}
          <span className="mono">subscription.charged.failed</span>.
        </p>
      </Panel>

      <Panel title="Notification preferences">
        <p className="settings-desc">
          Channel selection is not yet wired to the executor — outreach channel is chosen by the
          planner from the failure type. These are shown for completeness and have no effect on
          delivery.
        </p>
        <div className="toggles">
          {["WhatsApp recovery messages", "Hinglish SMS", "Email recovery"].map((t) => (
            <div className="toggle-row" key={t}>
              <span className="toggle toggle-on" aria-hidden="true" />
              <span className="muted">{t}</span>
              <span className="mono dim">planner-controlled</span>
            </div>
          ))}
        </div>
      </Panel>
    </>
  );
}
