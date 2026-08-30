import { forwardRef } from "react";
import { label as fmtLabel } from "../../lib/format.js";

/* Button — accent is reserved for the primary action on a screen. */
export function Button({ variant = "primary", as: As = "button", children, ...rest }) {
  return (
    <As className={`btn btn-${variant}`} {...rest}>
      {children}
    </As>
  );
}

/* Pill — the one place a 4px radius is allowed. */
const PILL_TONE = {
  recovered: "success",
  success: "success",
  nemotron_ok: "success",
  halted: "accent",
  outreach_sent: "accent",
  escalated: "danger",
  retry_failed: "danger",
  failed: "danger",
};

export function Pill({ tone, children }) {
  const resolved = tone || PILL_TONE[String(children).toLowerCase()] || "muted";
  return <span className={`pill pill-${resolved}`}>{fmtLabel(children)}</span>;
}

/* MetricCard — the headline numbers. Mono, large, accent only for money. */
export function MetricCard({ label, value, tone = "default", hint }) {
  return (
    <div className="metric">
      <div className={`metric-value mono tone-${tone}`}>{value}</div>
      <div className="metric-label">{label}</div>
      {hint && <div className="metric-hint mono">{hint}</div>}
    </div>
  );
}

/* Status dot — pulses accent while the socket is live. */
export function StatusDot({ on, labelText = "LIVE" }) {
  return (
    <span className="status">
      <span className={`dot ${on ? "dot-on" : "dot-off"}`} />
      <span className="mono status-text">{on ? labelText : "OFFLINE"}</span>
    </span>
  );
}

export function ProgressDots({ total, current }) {
  return (
    <div className="progress-dots" role="progressbar" aria-valuenow={current} aria-valuemin={1} aria-valuemax={total}>
      {Array.from({ length: total }, (_, i) => (
        <span key={i} className={`pdot ${i + 1 === current ? "pdot-active" : ""}`} />
      ))}
      <span className="sr-only">{`Step ${current} of ${total}`}</span>
    </div>
  );
}

export function Panel({ title, actions, children, className = "" }) {
  return (
    <section className={`panel ${className}`}>
      {(title || actions) && (
        <header className="panel-head">
          <h2 className="panel-title">{title}</h2>
          {actions}
        </header>
      )}
      <div className="panel-body">{children}</div>
    </section>
  );
}

export function Select({ value, onChange, options, placeholder }) {
  return (
    <select className="mono" value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">{placeholder}</option>
      {options.map((o) => (
        <option key={o} value={o}>
          {fmtLabel(o)}
        </option>
      ))}
    </select>
  );
}

/* Progress bar — accent fill on a dark track. */
export const ProgressBar = forwardRef(function ProgressBar({ value, max }, ref) {
  const p = max ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="pbar" ref={ref}>
      <div className="pbar-fill" style={{ width: `${p}%` }} />
    </div>
  );
});
