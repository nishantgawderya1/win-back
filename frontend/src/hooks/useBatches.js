import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api.js";

// Batch list for the dashboard. Re-polls while any batch is still running so
// the recent-batches table and the active count stay honest without a reload.
export function useBatches(limit = 10) {
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setBatches(await api.batches(limit));
    } catch {
      /* leave the previous list in place */
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    let timer;
    let cancelled = false;
    const tick = async () => {
      await refresh();
      if (cancelled) return;
      timer = setTimeout(tick, 4000);
    };
    tick();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [refresh]);

  const active = batches.filter((b) => b.status !== "complete");
  return { batches, active, loading, refresh };
}
