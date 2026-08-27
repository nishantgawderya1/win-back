import { useEffect, useState } from "react";
import LiveFeed from "./components/LiveFeed.jsx";
import BatchResults from "./components/BatchResults.jsx";
import AuditTrail from "./components/AuditTrail.jsx";
import HaltedActions from "./components/HaltedActions.jsx";
import ExceptionList from "./components/ExceptionList.jsx";
import { useWebSocket } from "./hooks/useWebSocket.js";
import { useBatch } from "./hooks/useBatch.js";
import { api } from "./lib/api.js";
import "./styles.css";

export default function App() {
  const { events, connected } = useWebSocket();
  const [batchId, setBatchId] = useState(null);
  const { status, results } = useBatch(batchId);

  const [summary, setSummary] = useState(null);
  const [exceptions, setExceptions] = useState([]);
  const [halted, setHalted] = useState([]);

  useEffect(() => {
    if (results?.batch?.status === "complete" && batchId) {
      api.summary(batchId).then(setSummary).catch(() => {});
      api.exceptions(batchId).then(setExceptions).catch(() => {});
      api.halted(batchId).then(setHalted).catch(() => {});
    }
  }, [results, batchId]);

  const onUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const res = await api.uploadBatch(file);
    setBatchId(res.batch_id);
  };

  return (
    <div className="app">
      <header>
        <h1>WinBack AI</h1>
        <div className="uploader">
          <label className="btn">
            Upload batch CSV
            <input type="file" accept=".csv" onChange={onUpload} hidden />
          </label>
          {status && (
            <span className="progress">
              {status.processed}/{status.total} — {status.status}
            </span>
          )}
        </div>
      </header>

      <div className="grid">
        <LiveFeed events={events} connected={connected} />
        <BatchResults summary={summary} />
        <HaltedActions halted={halted} />
        <ExceptionList exceptions={exceptions} />
        <AuditTrail events={events} batchId={batchId} />
      </div>
    </div>
  );
}
