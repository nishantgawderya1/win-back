// Live agent-action cards over WebSocket. The pitch-video money shot.
export default function LiveFeed({ events, connected }) {
  return (
    <div className="panel">
      <h2>
        Live Feed{" "}
        <span className={connected ? "dot dot-on" : "dot dot-off"} />
      </h2>
      <div className="feed">
        {events.length === 0 && <p className="muted">Waiting for agent actions…</p>}
        {events.map((e, i) => (
          <div className="card" key={i}>
            <div className="card-head">
              <span className="agent">{e.agent}</span>
              <span className="action">{e.action}</span>
              {e.outcome && <span className="outcome">{e.outcome}</span>}
            </div>
            <div className="reason">{e.reason}</div>
            <div className="meta">
              <span>{e.payment_id}</span>
              <span>₹{Number(e.amount || 0).toLocaleString("en-IN")}</span>
              <span>{new Date(e.timestamp).toLocaleTimeString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
