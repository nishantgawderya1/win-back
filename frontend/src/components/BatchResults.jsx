import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

// Recovery metric cards + breakdown-by-failure-type bar chart.
export default function BatchResults({ summary }) {
  if (!summary) return null;
  const inr = (n) => `₹${Number(n || 0).toLocaleString("en-IN")}`;

  const chartData = Object.entries(summary.by_failure_type || {}).map(([type, v]) => ({
    type,
    atRisk: v.at_risk,
    recovered: v.recovered,
  }));

  return (
    <div className="panel">
      <h2>Batch Results</h2>
      <div className="metrics">
        <Metric label="Total at risk" value={inr(summary.total_at_risk)} />
        <Metric label="Total recovered" value={inr(summary.total_recovered)} />
        <Metric label="Recovery rate" value={`${((summary.recovery_rate || 0) * 100).toFixed(1)}%`} />
      </div>
      <div style={{ height: 260 }}>
        <ResponsiveContainer>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="type" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="atRisk" name="At risk" fill="#94a3b8" />
            <Bar dataKey="recovered" name="Recovered" fill="#22c55e" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}
