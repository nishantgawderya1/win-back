import { useEffect, useMemo, useRef, useState } from "react";
import { FEED_BLOCKS } from "../../data/landingFeedScript.js";

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/**
 * The signature visual: a terminal-style panel replaying agent decisions.
 *
 * The full script is rendered on first paint rather than revealed from empty,
 * so the hero is never a blank box waiting on a timer — the animation only
 * controls which rows have arrived. With reduced motion, every row is present
 * immediately and nothing animates.
 */
export default function LandingFeed() {
  const flat = useMemo(
    () =>
      FEED_BLOCKS.flatMap((block, bi) =>
        block.lines.map((line, li) => ({
          ...line,
          paymentId: block.id,
          first: li === 0,
          key: `${bi}-${li}`,
        }))
      ),
    []
  );

  const reduced = useRef(prefersReducedMotion());
  const [count, setCount] = useState(reduced.current ? flat.length : 3);

  useEffect(() => {
    if (reduced.current) return undefined;
    const tick = setTimeout(
      () => setCount((c) => (c >= flat.length ? 3 : c + 1)),
      count >= flat.length ? 3200 : 1600
    );
    return () => clearTimeout(tick);
  }, [count, flat.length]);

  const visible = flat.slice(0, count);

  return (
    <div className="lfeed" aria-label="Live agent decision log">
      <div className="lfeed-head">
        <span className="mono lfeed-title">LIVE FEED</span>
        <span className="mono lfeed-status">
          <span className="dot dot-on" /> PROCESSING BATCH_001
        </span>
      </div>
      <div className="lfeed-body">
        {visible.map((l) => (
          <div
            key={l.key}
            className={`lfeed-row ${l.first ? "lfeed-row-first" : ""} lfeed-${l.tone || "plain"}`}
          >
            <span className="lfeed-at mono">{l.at}</span>
            <span className="lfeed-agent mono">{l.agent}</span>
            <span className="lfeed-arrow mono">→</span>
            <span className="lfeed-text mono">
              {l.first ? l.paymentId : l.text}
              {!l.first && <span className="lfeed-sep mono">:</span>}
            </span>
            <span className={`lfeed-value mono ${l.tone === "recovered" ? "lfeed-recovered" : ""}`}>
              {l.first ? `${l.text}: ${l.value}` : l.value}
              {l.tone === "recovered" && <span className="lfeed-check"> ✓</span>}
            </span>
          </div>
        ))}
      </div>
      <div className="lfeed-foot mono dim">
        Representative output. Every line is persisted to the audit trail.
      </div>
    </div>
  );
}
