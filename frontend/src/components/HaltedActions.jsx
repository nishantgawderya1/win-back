// What the agent decided NOT to do, and which rule fired. Builds trust.
export default function HaltedActions({ halted }) {
  return (
    <div className="panel">
      <h2>Halted Actions</h2>
      {(!halted || halted.length === 0) && <p className="muted">No halts in this batch.</p>}
      <div className="halt-list">
        {(halted || []).map((h, i) => (
          <div className="halt" key={i}>
            <div className="halt-head">
              <span>{h.payment_id}</span>
              <span className="prevented">prevented: {h.action}</span>
            </div>
            <div className="reason">{h.halt_reason}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
