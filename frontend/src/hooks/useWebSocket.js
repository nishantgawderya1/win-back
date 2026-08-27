import { useEffect, useRef, useState } from "react";

// Subscribes to /ws/feed and accumulates agent-action events.
export function useWebSocket(maxEvents = 200) {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    let retry;
    const connect = () => {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${proto}://${location.host}/ws/feed`);
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
      clearTimeout(retry);
      wsRef.current?.close();
    };
  }, [maxEvents]);

  return { events, connected };
}
