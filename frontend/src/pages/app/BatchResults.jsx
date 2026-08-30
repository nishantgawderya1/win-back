import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader } from "../../layouts/AppLayout.jsx";
import { MetricCard, Panel, Pill, ProgressBar } from "../../components/common/index.jsx";
import DataTable from "../../components/common/DataTable.jsx";
import { useBatch } from "../../hooks/useBatch.js";
import { api } from "../../lib/api.js";
import { inr, inrCompact, label, pct } from "../../lib/format.js";

const rateTone = (r) => (r >= 0.5 ? "success" : r >= 0.3 ? "amber" : "danger");

function statusOf(r) {
  if (r.recovered) return "recovered";
  if (r.halted) return "halted";
  if (r.escalated) return "escalated";
  return "pending";
}

export default function BatchResults() {
  const { id } = useParams();
  const { status, results } = useBatch(id);
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    if (results?.batch?.status !== "complete") return;
    api.summary(id).then(setSummary).catch(() => setSummary(null));
  }, [results, id]);

  const batch = results?.batch;
  const records = results?.records || [];
  const chartData = Object.entries(summary?.by_failure_type || {}).map(([type, v]) => ({
    type: label(type),
    atRisk: v.at_risk,
    recovered: v.recovered,
  }));

  return (
    <>
      <PageHeader
        title="Batch results"
        meta={`${id} · ${status ? `${status.processed}/${status.total} processed` : "loading"}${
          batch ? ` · ${batch.status}` : ""
        }`}
        actions={
          <a className="btn btn-ghost" href={api.auditExportUrl(id)}>
            Export audit CSV
          </a>
        }
      />

      {status && status.status !== "complete" && (
        <Panel title="Processing">
          <ProgressBar value={status.processed} max={status.total} />
          <p className="mono dim batch-count">
            {status.processed} / {status.total} — the agent is working through the batch.
          </p>
        </Panel>
      )}

      <div className="metrics">
        <MetricCard label="Total at risk" value={inrCompact(batch?.total_at_risk)} />
        <MetricCard label="Total recovered" value={inrCompact(batch?.total_recovered)} tone="amber" />
        <MetricCard
          label="Recovery rate"
          value={pct(batch?.recovery_rate)}
          tone={rateTone(batch?.recovery_rate || 0)}
        />
        <MetricCard label="Records" value={String(batch?.total_records ?? "—")} />
      </div>

      <div className="results-grid">
        <Panel title="At risk vs recovered">
          {chartData.length === 0 ? (
            <p className="empty muted">Waiting for the batch to finish.</p>
          ) : (
            <div style={{ height: 280 }}>
              <ResponsiveContainer>
                <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
                  <XAxis
                    dataKey="type"
                    tick={{ fontSize: 10, fontFamily: "JetBrains Mono, monospace", fill: "#8b909a" }}
                    axisLine={{ stroke: "#1e2229" }}
                    tickLine={false}
                    interval={0}
                    angle={-18}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fontFamily: "JetBrains Mono, monospace", fill: "#8b909a" }}
                    axisLine={{ stroke: "#1e2229" }}
                    tickLine={false}
                    tickFormatter={(v) => inrCompact(v)}
                    width={64}
                  />
                  <Tooltip
                    cursor={{ fill: "rgba(245,158,11,0.06)" }}
                    contentStyle={{
                      background: "#0a0b0f",
                      border: "1px solid #1e2229",
                      borderRadius: 0,
                      fontFamily: "JetBrains Mono, monospace",
                      fontSize: 12,
                    }}
                    formatter={(v, n) => [inr(v), n]}
                  />
                  <Bar dataKey="atRisk" name="At risk" fill="#1e2229" />
                  <Bar dataKey="recovered" name="Recovered" fill="#f59e0b" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>

        <Panel title="By failure type">
          <DataTable
            rows={Object.entries(summary?.by_failure_type || {}).map(([type, v]) => ({
              type,
              ...v,
            }))}
            rowKey={(r) => r.type}
            empty="No breakdown yet."
            columns={[
              {
                key: "type",
                header: "failure type",
                render: (r) => <span className="mono">{label(r.type)}</span>,
              },
              {
                key: "count",
                header: "count",
                render: (r) => <span className="mono">{r.count}</span>,
              },
              {
                key: "at_risk",
                header: "at risk",
                render: (r) => <span className="mono muted">{inr(r.at_risk)}</span>,
              },
              {
                key: "recovered",
                header: "recovered",
                render: (r) => (
                  <span className={`mono ${r.recovered > 0 ? "amber" : "dim"}`}>
                    {inr(r.recovered)}
                  </span>
                ),
              },
              {
                key: "rate",
                header: "rate",
                render: (r) => (
                  <span className="mono">{pct(r.at_risk ? r.recovered / r.at_risk : 0)}</span>
                ),
              },
            ]}
          />
        </Panel>
      </div>

      <Panel title="Payments">
        <DataTable
          rows={records}
          rowKey={(r) => r.payment_id}
          empty="No payment records yet."
          renderExpanded={(r) => (
            <div className="expand">
              <div className="expand-row">
                <span className="expand-key mono dim">root cause</span>
                <span>{r.root_cause || "—"}</span>
              </div>
              <div className="expand-row">
                <span className="expand-key mono dim">confidence</span>
                <span className="mono">
                  {r.confidence == null ? "—" : r.confidence.toFixed(2)}
                </span>
              </div>
              <div className="expand-row">
                <span className="expand-key mono dim">recovery score</span>
                <span className="mono">
                  {r.customer_recovery_score == null
                    ? "—"
                    : r.customer_recovery_score.toFixed(2)}
                </span>
              </div>
              {(r.halt_reason || r.escalation_reason) && (
                <div className="expand-row">
                  <span className="expand-key mono dim">
                    {r.halted ? "halt reason" : "escalation"}
                  </span>
                  <span className="amber">{r.halt_reason || r.escalation_reason}</span>
                </div>
              )}
              <div className="expand-row">
                <span className="expand-key mono dim">reasoning</span>
                <ul className="reasoning">
                  {(r.agent_reasoning || []).length === 0 ? (
                    <li className="dim">No reasoning chain recorded.</li>
                  ) : (
                    r.agent_reasoning.map((line, i) => <li key={i}>{line}</li>)
                  )}
                </ul>
              </div>
            </div>
          )}
          columns={[
            {
              key: "payment_id",
              header: "payment_id",
              render: (r) => <span className="mono amber">{r.payment_id}</span>,
            },
            {
              key: "amount",
              header: "amount",
              render: (r) => (
                <span className={`mono ${r.recovered ? "amber" : "muted"}`}>{inr(r.amount)}</span>
              ),
            },
            {
              key: "failure_type",
              header: "failure",
              render: (r) => <span className="mono muted">{label(r.failure_type)}</span>,
            },
            {
              key: "intervention",
              header: "intervention",
              render: (r) => <span className="mono">{label(r.intervention)}</span>,
            },
            {
              key: "attempt_count",
              header: "attempts",
              render: (r) => <span className="mono">{r.attempt_count}</span>,
            },
            {
              key: "status",
              header: "status",
              render: (r) => <Pill>{statusOf(r)}</Pill>,
            },
          ]}
        />
      </Panel>
    </>
  );
}
