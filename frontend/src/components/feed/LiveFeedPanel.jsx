import { useEffect, useRef, useState } from "react";
import AgentEventCard from "./AgentEventCard.jsx";
import { StatusDot } from "../common/index.jsx";

/**
 * The live agent-action stream. Shared by the dashboard and the full-screen
 * feed screen; the landing page has its own scripted variant.
 */
export default function LiveFeedPanel({ events, connected, title = "Live Feed", max = 60, children }) {
  const [freshKey, setFreshKey] = useState(null);
  const seen = useRef(new Set());

  // Flash only genuinely new recovery events, not every re-render.
  useEffect(() => {
    const top = events[0];
    if (!top) return;
    const id = `${top.payment_id}-${top.timestamp}-${top.action}`;
    if (seen.current.has(id)) return;
    seen.current.add(id);
    if (top.outcome === "recovered") {
      setFreshKey(id);
      const t = setTimeout(() => setFreshKey(null), 1200);
      return () => clearTimeout(t);
    }
  }, [events]);

  const shown = events.slice(0, max);

  return (
    <section className="panel feed-panel">
      <header className="panel-head">
        <h2 className="panel-title">
          {title} <StatusDot on={connected} />
        </h2>
        {children}
      </header>
      <div className="feed">
        {shown.length === 0 && (
          <p className="empty muted">
            Waiting for agent actions. Upload a batch to start the pipeline.
          </p>
        )}
        {shown.map((e) => {
          const id = `${e.payment_id}-${e.timestamp}-${e.action}`;
          return <AgentEventCard key={id} event={e} isNew={id === freshKey} />;
        })}
      </div>
    </section>
  );
}
