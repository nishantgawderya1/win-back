// Every payment that could NOT be recovered, one row each. The honest metric.
export default function ExceptionList({ exceptions }) {
  const inr = (n) => `₹${Number(n || 0).toLocaleString("en-IN")}`;
  return (
    <div className="panel">
      <h2>Exception List</h2>
      {(!exceptions || exceptions.length === 0) && (
        <p className="muted">Nothing unresolved.</p>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>payment_id</th>
              <th>amount</th>
              <th>failure</th>
              <th>reason</th>
            </tr>
          </thead>
          <tbody>
            {(exceptions || []).map((e, i) => (
              <tr key={i}>
                <td>{e.payment_id}</td>
                <td>{inr(e.amount)}</td>
                <td>{e.failure_type}</td>
                <td className="reason-cell">{e.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
