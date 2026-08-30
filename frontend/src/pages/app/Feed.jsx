import { useEffect, useMemo, useRef, useState } from "react";
import { PageHeader } from "../../layouts/AppLayout.jsx";
import AgentEventCard from "../../components/feed/AgentEventCard.jsx";
import { Select, StatusDot } from "../../components/common/index.jsx";
import { useWebSocket } from "../../hooks/useWebSocket.js";

const AGENTS = [
  "detection",
  "diagnosis",
  "planner",
  "executor",
  "monitor",
  "reporter",
  "halt",
  "escalate",
];

const OUTCOMES = [
  "recovered",
  "retry_failed",
  "outreach_sent",
  "halted",
  "escalated",
  "completed",
  "nemotron_ok",
  "fallback_rules",
  "unresolved",
];

/**
 * Full-screen agent stream. Filters apply client-side over the live socket —
 * the feed is a tail of what is happening now, not a database query. Use the
 * Audit Trail screen for history.
 */
export default function Feed() {
  const { events, connected } = useWebSocket(400);
  const [agent, setAgent] = useState("");
  const [outcome, setOutcome] = useState("");
  const [batchId, setBatchId] = useState("");

  const batches = useMemo(
    () => [...new Set(events.map((e) => e.batch_id).filter(Boolean))],
    [events]
  );

  const filtered = events.filter(
    (e) =>
      (!agent || e.agent === agent) &&
      (!outcome || e.outcome === outcome) &&
      (!batchId || e.batch_id === batchId)
  );

  // Flash the newest recovery exactly once, as it lands.
  const [freshKey, setFreshKey] = useState(null);
  const seen = useRef(new Set());
  useEffect(() => {
    const top = events[0];
    if (!top) return undefined;
    const key = `${top.payment_id}-${top.timestamp}-${top.action}`;
    if (seen.current.has(key)) return undefined;
    seen.current.add(key);
    if (top.outcome !== "recovered") return undefined;
    setFreshKey(key);
    const t = setTimeout(() => setFreshKey(null), 1200);
    return () => clearTimeout(t);
  }, [events]);

  return (
    <>
      <PageHeader
        title="Live Feed"
        meta={`${filtered.length} events${events.length !== filtered.length ? ` of ${events.length}` : ""}`}
        actions={<StatusDot on={connected} />}
      />

      <div className="toolbar">
        <Select value={agent} onChange={setAgent} options={AGENTS} placeholder="All agents" />
        <Select
          value={outcome}
          onChange={setOutcome}
          options={OUTCOMES}
          placeholder="All outcomes"
        />
        <Select
          value={batchId}
          onChange={setBatchId}
          options={batches}
          placeholder="All batches"
        />
        {(agent || outcome || batchId) && (
          <button
            className="linkish mono"
            onClick={() => {
              setAgent("");
              setOutcome("");
              setBatchId("");
            }}
          >
            clear filters
          </button>
        )}
      </div>

      <div className="feed feed-full">
        {filtered.length === 0 && (
          <p className="empty muted">
            {events.length === 0
              ? "Waiting for agent actions. Upload a batch to start the pipeline."
              : "No events match these filters."}
          </p>
        )}
        {filtered.map((e) => {
          const key = `${e.payment_id}-${e.timestamp}-${e.action}`;
          return <AgentEventCard key={key} event={e} isNew={key === freshKey} />;
        })}
      </div>
    </>
  );
}
