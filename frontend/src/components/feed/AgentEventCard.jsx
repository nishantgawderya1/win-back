import { inr, label, time } from "../../lib/format.js";

/**
 * One agent action in the live stream.
 *
 * The top border carries the outcome: amber for recovered money, green for a
 * clean action, red for a failure, muted while in progress. A recovered event
 * flashes once when it arrives — the most significant visual moment in the
 * product, so nothing else on the page is allowed to compete with it.
 */
const TONE = {
  recovered: "recovered",
  outreach_sent: "amber",
  halted: "amber",
  escalated: "danger",
  retry_failed: "danger",
  completed: "success",
  nemotron_ok: "success",
  fallback_rules: "muted",
};

export default function AgentEventCard({ event, isNew }) {
  const tone = TONE[event.outcome] || "muted";
  const isRecovery = event.outcome === "recovered";

  return (
    <article className={`event event-${tone} ${isNew && isRecovery ? "event-flash" : ""}`}>
      <div className="event-head">
        <span className="event-agent mono">{label(event.agent)}</span>
        <time className="event-time mono dim" dateTime={event.timestamp}>
          {time(event.timestamp)}
        </time>
      </div>
      <div className="event-action mono">{event.action}</div>
      <p className="event-reason">{event.reason}</p>
      <div className="event-meta">
        <span className="mono event-pid">{event.payment_id}</span>
        <span className={`mono ${isRecovery ? "amber" : "dim"}`}>{inr(event.amount)}</span>
        {event.outcome && <span className={`pill pill-${tone}`}>{label(event.outcome)}</span>}
      </div>
    </article>
  );
}
