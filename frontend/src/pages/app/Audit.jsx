import { useCallback, useEffect, useState } from "react";
import { PageHeader } from "../../layouts/AppLayout.jsx";
import { Panel, Select } from "../../components/common/index.jsx";
import DataTable from "../../components/common/DataTable.jsx";
import { api } from "../../lib/api.js";
import { dateTime, inr, label, truncate } from "../../lib/format.js";

const AGENTS = [
  "detection",
  "diagnosis",
  "planner",
  "executor",
  "monitor",
  "reporter",
  "halt",
  "escalate",
];

const OUTCOMES = [
  "recovered",
  "retry_failed",
  "outreach_sent",
  "halted",
  "escalated",
  "completed",
  "nemotron_ok",
  "fallback_rules",
  "unresolved",
];

/**
 * The full audit trail, queried from the database rather than the socket.
 *
 * Clicking a payment id loads that payment's complete decision chain inline —
 * the deepest drill-down in the product.
 */
export default function Audit() {
  const [entries, setEntries] = useState([]);
  const [batches, setBatches] = useState([]);
  const [filters, setFilters] = useState({ agent: "", outcome: "", batch_id: "" });
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.batches(50).then((b) => setBatches(b.map((x) => x.id))).catch(() => {});
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setEntries(await api.audit({ ...filters, limit: 300 }));
    } catch {
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    load();
  }, [load]);

  const openPayment = async (paymentId) => {
    if (detail?.record?.payment_id === paymentId || detail?.id === paymentId) {
      setDetail(null);
      return;
    }
    try {
      const d = await api.payment(paymentId);
      setDetail({ ...d, id: paymentId });
    } catch {
      setDetail(null);
    }
  };

  const set = (k) => (v) => setFilters((f) => ({ ...f, [k]: v }));

  return (
    <>
      <PageHeader
        title="Audit Trail"
        meta={loading ? "loading…" : `${entries.length} entries`}
        actions={
          filters.batch_id ? (
            <a className="btn btn-ghost" href={api.auditExportUrl(filters.batch_id)}>
              Export CSV
            </a>
          ) : (
            <span className="mono dim">select a batch to export</span>
          )
        }
      />

      <div className="toolbar">
        <Select value={filters.agent} onChange={set("agent")} options={AGENTS} placeholder="All agents" />
        <Select
          value={filters.outcome}
          onChange={set("outcome")}
          options={OUTCOMES}
          placeholder="All outcomes"
        />
        <Select
          value={filters.batch_id}
          onChange={set("batch_id")}
          options={batches}
          placeholder="All batches"
        />
        {(filters.agent || filters.outcome || filters.batch_id) && (
          <button
            className="linkish mono"
            onClick={() => setFilters({ agent: "", outcome: "", batch_id: "" })}
          >
            clear filters
          </button>
        )}
        <button className="linkish mono" onClick={load}>
          refresh
        </button>
      </div>

      {detail && (
        <Panel title={`Decision chain — ${detail.id}`}>
          {detail.record && (
            <div className="expand">
              <div className="expand-row">
                <span className="expand-key mono dim">amount</span>
                <span className={`mono ${detail.record.recovered ? "accent" : "muted"}`}>
                  {inr(detail.record.amount)}
                </span>
              </div>
              <div className="expand-row">
                <span className="expand-key mono dim">root cause</span>
                <span>{detail.record.root_cause || "—"}</span>
              </div>
              <div className="expand-row">
                <span className="expand-key mono dim">intervention</span>
                <span className="mono">{label(detail.record.intervention)}</span>
              </div>
            </div>
          )}
          <ol className="chain">
            {detail.audit_trail.map((e, i) => (
              <li key={i} className="chain-step">
                <span className="mono dim chain-time">{dateTime(e.timestamp)}</span>
                <span className="mono chain-agent">{label(e.agent)}</span>
                <span className="chain-reason">{e.reason}</span>
                {e.outcome && <span className="mono accent chain-outcome">{e.outcome}</span>}
              </li>
            ))}
          </ol>
          <button className="linkish mono" onClick={() => setDetail(null)}>
            close
          </button>
        </Panel>
      )}

      <Panel title="Entries">
        <DataTable
          rows={entries}
          rowKey={(e, i) => `${e.payment_id}-${e.timestamp}-${i}`}
          empty="No audit entries match these filters."
          renderExpanded={(e) => (
            <div className="expand">
              <div className="expand-row">
                <span className="expand-key mono dim">reason</span>
                <span>{e.reason}</span>
              </div>
              <div className="expand-row">
                <span className="expand-key mono dim">batch</span>
                <span className="mono">{e.batch_id}</span>
              </div>
              <button
                className="linkish mono"
                onClick={(ev) => {
                  ev.stopPropagation();
                  openPayment(e.payment_id);
                }}
              >
                view full decision chain for {e.payment_id} →
              </button>
            </div>
          )}
          columns={[
            {
              key: "timestamp",
              header: "timestamp",
              render: (e) => <span className="mono dim">{dateTime(e.timestamp)}</span>,
            },
            {
              key: "payment_id",
              header: "payment_id",
              render: (e) => <span className="mono accent">{e.payment_id}</span>,
            },
            {
              key: "agent",
              header: "agent",
              render: (e) => <span className="mono dim">{label(e.agent)}</span>,
            },
            {
              key: "action",
              header: "action",
              render: (e) => <span className="mono">{e.action}</span>,
            },
            {
              key: "reason",
              header: "reason",
              className: "reason-cell",
              render: (e) => <span className="muted">{truncate(e.reason, 88)}</span>,
            },
            {
              key: "outcome",
              header: "outcome",
              render: (e) =>
                e.outcome ? (
                  <span className={`pill pill-${e.outcome === "recovered" ? "recovered" : "muted"}`}>
                    {label(e.outcome)}
                  </span>
                ) : (
                  <span className="dim mono">—</span>
                ),
            },
          ]}
        />
      </Panel>
    </>
  );
}
