import { useEffect, useRef, useState } from "react";
import { getAccessToken } from "../lib/supabase.js";

// Subscribes to /ws/feed and accumulates agent-action events.
export function useWebSocket(maxEvents = 200) {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    let retry;
    let closed = false;
    const connect = async () => {
      if (closed) return;
      const proto = location.protocol === "https:" ? "wss" : "ws";
      // A browser cannot set headers on a WebSocket handshake, so the access
      // token travels as a query parameter. The server verifies and discards
      // it without logging.
      const token = await getAccessToken();
      const query = token ? `?token=${encodeURIComponent(token)}` : "";
      const ws = new WebSocket(`${proto}://${location.host}/ws/feed${query}`);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        retry = setTimeout(connect, 2000);
      };
      ws.onmessage = (msg) => {
        try {
          const event = JSON.parse(msg.data);
          setEvents((prev) => [event, ...prev].slice(0, maxEvents));
        } catch {
          /* ignore malformed */
        }
      };
    };
    connect();
    return () => {
      closed = true;
      clearTimeout(retry);
      wsRef.current?.close();
    };
  }, [maxEvents]);

  return { events, connected };
}
