import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

// Polls batch status until complete, then returns results.
export function useBatch(batchId) {
  const [status, setStatus] = useState(null);
  const [results, setResults] = useState(null);

  useEffect(() => {
    if (!batchId) return;
    let timer;
    const poll = async () => {
      try {
        const s = await api.batchStatus(batchId);
        setStatus(s);
        if (s.status === "complete") {
          setResults(await api.batchResults(batchId));
          return;
        }
      } catch {
        /* keep polling */
      }
      timer = setTimeout(poll, 1500);
    };
    poll();
    return () => clearTimeout(timer);
  }, [batchId]);

  return { status, results };
}
