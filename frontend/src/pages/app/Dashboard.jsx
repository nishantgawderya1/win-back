import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../layouts/AppLayout.jsx";
import LiveFeedPanel from "../../components/feed/LiveFeedPanel.jsx";
import { MetricCard, Panel, ProgressBar } from "../../components/common/index.jsx";
import DataTable from "../../components/common/DataTable.jsx";
import { useWebSocket } from "../../hooks/useWebSocket.js";
import { useBatches } from "../../hooks/useBatches.js";
import { api } from "../../lib/api.js";
import { dateTime, inr, inrCompact, label, pct } from "../../lib/format.js";

// Recovery rate is the one metric that earns a colour by value.
const rateTone = (r) => (r >= 0.5 ? "success" : r >= 0.3 ? "amber" : "danger");

export default function Dashboard() {
  const { events, connected } = useWebSocket();
  const { batches, active } = useBatches(10);
  const [summary, setSummary] = useState(null);

  // Headline figures track the most recent batch that has finished.
  const latestComplete = useMemo(
    () => batches.find((b) => b.status === "complete"),
    [batches]
  );

  useEffect(() => {
    if (!latestComplete) return;
    api.summary(latestComplete.id).then(setSummary).catch(() => setSummary(null));
  }, [latestComplete]);

  const current = active[0];

  return (
    <>
      <PageHeader
        title="Dashboard"
        meta={latestComplete ? `latest batch ${latestComplete.id}` : "no completed batches yet"}
        actions={
          <Link to="/batch" className="btn btn-amber">
            New batch
          </Link>
        }
      />

      <div className="metrics">
        <MetricCard label="Total at risk" value={inrCompact(summary?.total_at_risk)} />
        <MetricCard
          label="Total recovered"
          value={inrCompact(summary?.total_recovered)}
          tone="amber"
        />
        <MetricCard
          label="Recovery rate"
          value={pct(summary?.recovery_rate)}
          tone={rateTone(summary?.recovery_rate || 0)}
        />
        <MetricCard label="Active batches" value={String(active.length)} />
      </div>

      <div className="dash-grid">
        <LiveFeedPanel events={events} connected={connected} max={40}>
          <Link to="/feed" className="linkish mono">
            full screen →
          </Link>
        </LiveFeedPanel>

        <div className="dash-side">
          <Panel title="Batch status">
            {current ? (
              <>
                <div className="mono dim batch-id">{current.id}</div>
                <ProgressBar value={current.processed} max={current.total_records} />
                <div className="mono batch-count">
                  {current.processed} / {current.total_records} processed
                </div>
              </>
            ) : (
              <p className="empty muted">No batch running.</p>
            )}

            {summary?.by_failure_type && (
              <div className="ftype-bars">
                {Object.entries(summary.by_failure_type).map(([type, v]) => (
                  <div className="ftype" key={type}>
                    <div className="ftype-head mono">
                      <span className="muted">{label(type)}</span>
                      <span className={v.recovered > 0 ? "amber" : "dim"}>
                        {inrCompact(v.recovered)} / {inrCompact(v.at_risk)}
                      </span>
                    </div>
                    <ProgressBar value={v.recovered} max={v.at_risk} />
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>

      <Panel title="Recent batches">
        <DataTable
          rows={batches}
          rowKey={(b) => b.id}
          empty="No batches yet. Upload a CSV to run the pipeline."
          columns={[
            {
              key: "id",
              header: "batch_id",
              render: (b) => (
                <Link className="mono amber" to={`/batch/${b.id}`}>
                  {b.id}
                </Link>
              ),
            },
            {
              key: "created_at",
              header: "created",
              render: (b) => <span className="mono dim">{dateTime(b.created_at)}</span>,
            },
            {
              key: "total_records",
              header: "records",
              render: (b) => (
                <span className="mono">
                  {b.processed}/{b.total_records}
                </span>
              ),
            },
            {
              key: "total_at_risk",
              header: "at risk",
              render: (b) => <span className="mono muted">{inr(b.total_at_risk)}</span>,
            },
            {
              key: "total_recovered",
              header: "recovered",
              render: (b) => (
                <span className={`mono ${b.total_recovered > 0 ? "amber" : "dim"}`}>
                  {inr(b.total_recovered)}
                </span>
              ),
            },
            {
              key: "recovery_rate",
              header: "rate",
              render: (b) => <span className="mono">{pct(b.recovery_rate)}</span>,
            },
            {
              key: "status",
              header: "status",
              render: (b) => (
                <span className={`pill pill-${b.status === "complete" ? "success" : "amber"}`}>
                  {b.status.toUpperCase()}
                </span>
              ),
            },
          ]}
        />
      </Panel>
    </>
  );
}
