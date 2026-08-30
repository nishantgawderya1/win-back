import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../layouts/AppLayout.jsx";
import { Panel, Select } from "../../components/common/index.jsx";
import DataTable from "../../components/common/DataTable.jsx";
import { api } from "../../lib/api.js";
import { dateTime, inr, label } from "../../lib/format.js";

/**
 * What the agent decided NOT to do, and which rule stopped it.
 *
 * This screen exists to build trust: inaction here is a deliberate,
 * rules-based decision, not a failure of the pipeline.
 */
export default function Halted() {
  const [rows, setRows] = useState([]);
  const [batches, setBatches] = useState([]);
  const [batchId, setBatchId] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.batches(50).then((b) => setBatches(b.map((x) => x.id))).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    api
      .halted({ batch_id: batchId, limit: 300 })
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [batchId]);

  const totalWithheld = rows.reduce((s, r) => s + (r.amount_at_risk || 0), 0);

  return (
    <>
      <PageHeader
        title="Halted Actions"
        meta={loading ? "loading…" : `${rows.length} halts · ${inr(totalWithheld)} not pursued`}
        actions={
          <Select
            value={batchId}
            onChange={setBatchId}
            options={batches}
            placeholder="All batches"
          />
        }
      />

      <div className="callout callout-wide">
        <p>
          These are payments the agent chose not to act on. Each entry names the exact rule that
          prevented the action.
        </p>
        <p className="mono dim">
          Stopping rules are configurable in <Link to="/settings">Settings</Link>.
        </p>
      </div>

      <Panel title="Prevented actions">
        <DataTable
          rows={rows}
          rowKey={(r, i) => `${r.payment_id}-${r.timestamp}-${i}`}
          empty="No halts recorded. Every planned action passed the stopping rules."
          columns={[
            {
              key: "timestamp",
              header: "timestamp",
              render: (r) => <span className="mono dim">{dateTime(r.timestamp)}</span>,
            },
            {
              key: "payment_id",
              header: "payment_id",
              render: (r) => <span className="mono accent">{r.payment_id}</span>,
            },
            {
              key: "action",
              header: "action prevented",
              render: (r) => <span className="mono">{label(r.action)}</span>,
            },
            {
              key: "halt_reason",
              header: "stopping rule fired",
              className: "reason-cell",
              render: (r) => <span className="accent">{r.halt_reason}</span>,
            },
            {
              key: "amount_at_risk",
              header: "amount at risk",
              render: (r) => (
                <span className="mono muted">
                  {r.amount_at_risk == null ? "—" : inr(r.amount_at_risk)}
                </span>
              ),
            },
          ]}
        />
      </Panel>
    </>
  );
}
