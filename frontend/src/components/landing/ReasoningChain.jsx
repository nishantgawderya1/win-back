import { useEffect, useRef, useState } from "react";
import { inr, label } from "../../lib/format.js";

/**
 * A real diagnosis, quoted from a captured run.
 *
 * Every word here comes from demo-stats.json, which the snapshot script writes
 * from an actual batch — the root cause, the scores and each reasoning step are
 * Nemotron's own output. Nothing on this panel is written copy, which is the
 * point: a landing page claiming an agent reasons should show the reasoning.
 */
const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export default function ReasoningChain({ diagnosis }) {
  const steps = diagnosis?.reasoning || [];
  const reduced = useRef(prefersReducedMotion());
  const [shown, setShown] = useState(reduced.current ? steps.length : 0);

  useEffect(() => {
    if (reduced.current || steps.length === 0) return undefined;
    const t = setTimeout(
      () => setShown((n) => (n >= steps.length ? 0 : n + 1)),
      shown >= steps.length ? 3600 : 620
    );
    return () => clearTimeout(t);
  }, [shown, steps.length]);

  if (!diagnosis) return null;

  const score = diagnosis.customer_recovery_score;

  return (
    <div className="chain-panel">
      <header className="chain-head">
        <span className="mono chain-agent">DIAGNOSIS</span>
        <span className="mono chain-model">nemotron-3-super-120b</span>
      </header>

      <div className="chain-input mono">
        <span className="dim">input</span>
        <span>
          {diagnosis.payment_id} · {inr(diagnosis.amount)} ·{" "}
          {label(diagnosis.failure_type)}
        </span>
      </div>

      {/* Every step stays legible. The walk marks where the agent is, rather
          than hiding what it has not reached — the reasoning is the content,
          so dimming it to near-invisible defeated the point of showing it. */}
      <ol className="chain-steps">
        {steps.map((step, i) => (
          <li
            key={i}
            className={`chain-step ${i === shown - 1 ? "chain-step-active" : ""} ${
              i < shown ? "chain-step-seen" : ""
            }`}
          >
            <span className="mono chain-index">{String(i + 1).padStart(2, "0")}</span>
            <span>{step}</span>
          </li>
        ))}
      </ol>

      <div className="chain-verdict">
        <p className="chain-cause">{diagnosis.root_cause}</p>
        <div className="chain-scores mono">
          <span>
            <span className="dim">confidence</span>{" "}
            <strong className="accent">{Number(diagnosis.confidence).toFixed(2)}</strong>
          </span>
          {score != null && (
            <span>
              <span className="dim">recovery score</span>{" "}
              <strong className="accent">{Number(score).toFixed(2)}</strong>
            </span>
          )}
          <span>
            <span className="dim">action</span>{" "}
            <strong>{label(diagnosis.intervention)}</strong>
          </span>
        </div>
      </div>

      <footer className="chain-foot mono dim">
        Verbatim output from a captured run. The action was chosen by
        deterministic rules from these scores, not by the model.
      </footer>
    </div>
  );
}
