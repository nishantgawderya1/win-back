import { useEffect, useState } from "react";
import { PageHeader } from "../../layouts/AppLayout.jsx";
import { Panel, Pill, Select } from "../../components/common/index.jsx";
import DataTable from "../../components/common/DataTable.jsx";
import { api } from "../../lib/api.js";
import { inr, inrCompact, label } from "../../lib/format.js";

/** Every payment that could not be recovered, with its specific reason. */
export default function Exceptions() {
  const [data, setData] = useState(null);
  const [batches, setBatches] = useState([]);
  const [batchId, setBatchId] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.batches(50).then((b) => setBatches(b.map((x) => x.id))).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    api
      .exceptions({ batch_id: batchId, limit: 500 })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [batchId]);

  const rows = data?.records || [];

  return (
    <>
      <PageHeader
        title="Exceptions"
        meta={loading ? "loading…" : `${data?.count ?? 0} unresolved payments`}
        actions={
          <Select
            value={batchId}
            onChange={setBatchId}
            options={batches}
            placeholder="All batches"
          />
        }
      />

      <div className="unrecovered">
        <div className="unrecovered-value mono amber">{inrCompact(data?.total_unrecovered)}</div>
        <div className="eyebrow">Unrecovered</div>
        <p className="unrecovered-copy">
          These payments could not be recovered automatically. Each entry carries the specific
          reason. Escalated payments are waiting for human review in your Razorpay dashboard.
        </p>
        <div className="unrecovered-split mono">
          <span>
            <span className="dim">escalated</span> {data?.escalated_count ?? 0}
          </span>
          <span>
            <span className="dim">halted by rule</span> {data?.halted_count ?? 0}
          </span>
          <span>
            <span className="dim">attempted, unrecovered</span>{" "}
            {Math.max(
              0,
              (data?.count ?? 0) - (data?.escalated_count ?? 0) - (data?.halted_count ?? 0)
            )}
          </span>
        </div>
      </div>

      <Panel title="Unresolved payments">
        <DataTable
          rows={rows}
          rowKey={(r) => r.payment_id}
          empty="Nothing unresolved. Every payment in scope was recovered."
          columns={[
            {
              key: "payment_id",
              header: "payment_id",
              render: (r) => <span className="mono amber">{r.payment_id}</span>,
            },
            {
              key: "amount",
              header: "amount",
              render: (r) => <span className="mono muted">{inr(r.amount)}</span>,
            },
            {
              key: "failure_type",
              header: "failure",
              render: (r) => <span className="mono muted">{label(r.failure_type)}</span>,
            },
            {
              key: "reason",
              header: "reason unresolved",
              className: "reason-cell",
              render: (r) => <span>{r.reason}</span>,
            },
            {
              key: "attempt_count",
              header: "attempts",
              render: (r) => <span className="mono">{r.attempt_count}</span>,
            },
            {
              key: "escalated",
              header: "escalated",
              render: (r) =>
                r.escalated ? (
                  <Pill tone="danger">escalated</Pill>
                ) : r.halted ? (
                  <Pill tone="amber">halted</Pill>
                ) : (
                  <span className="dim mono">no</span>
                ),
            },
          ]}
        />
      </Panel>
    </>
  );
}
