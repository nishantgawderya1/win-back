import { api } from "../lib/api.js";

// Full agent-action log built from the live event stream, plus CSV export.
export default function AuditTrail({ events, batchId }) {
  return (
    <div className="panel">
      <h2>
        Audit Trail
        {batchId && (
          <a className="export" href={api.auditExportUrl(batchId)}>
            Export CSV
          </a>
        )}
      </h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>payment_id</th>
              <th>agent</th>
              <th>action</th>
              <th>reason</th>
              <th>outcome</th>
              <th>time</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e, i) => (
              <tr key={i}>
                <td>{e.payment_id}</td>
                <td>{e.agent}</td>
                <td>{e.action}</td>
                <td className="reason-cell">{e.reason}</td>
                <td>{e.outcome}</td>
                <td>{new Date(e.timestamp).toLocaleTimeString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
