import { useEffect, useRef, useState } from "react";

/**
 * The agent's actual control flow, drawn from backend/graph/graph.py.
 *
 * This is the load-bearing claim of the product — that recovery runs as a
 * bounded state machine rather than a model improvising — so the diagram shows
 * the real graph: every node, the three ways out of the planner, and the loop
 * back from monitor. The one node that calls an LLM is marked, because "AI
 * decides the diagnosis, deterministic code decides the action" is the whole
 * safety argument.
 *
 * A token walks the happy path so the structure reads as a process rather than
 * an org chart. Under reduced motion it simply sits at the end.
 */

// Node centres, in viewBox units. The two branch nodes sit above and below the
// main line so the three-way split out of `plan` is legible at a glance.
const N = {
  detect: { x: 78, y: 150, label: "detect", sub: "rules" },
  diagnose: { x: 218, y: 150, label: "diagnose", sub: "Nemotron", llm: true },
  plan: { x: 358, y: 150, label: "plan", sub: "guardrails" },
  execute: { x: 508, y: 150, label: "execute", sub: "tools" },
  monitor: { x: 648, y: 150, label: "monitor", sub: "outcome" },
  halt: { x: 508, y: 58, label: "halt", sub: "rule fired", tone: "stop" },
  escalate: { x: 508, y: 242, label: "escalate", sub: "human", tone: "warn" },
  report: { x: 800, y: 150, label: "report", sub: "audit" },
};

const W = 104;
const H = 46;

const EDGES = [
  { from: "detect", to: "diagnose" },
  { from: "diagnose", to: "plan" },
  { from: "plan", to: "execute" },
  { from: "execute", to: "monitor" },
  { from: "monitor", to: "report" },
  { from: "plan", to: "halt", kind: "branch" },
  { from: "plan", to: "escalate", kind: "branch" },
  { from: "halt", to: "report", kind: "branch" },
  { from: "escalate", to: "report", kind: "branch" },
];

// The path the animated token follows: the ordinary recovery route.
const WALK = ["detect", "diagnose", "plan", "execute", "monitor", "report"];

function edgePath(from, to) {
  const a = N[from];
  const b = N[to];
  const ax = a.x + W / 2;
  const bx = b.x - W / 2;

  if (a.y === b.y) return `M ${ax} ${a.y} L ${bx} ${b.y}`;

  // Branch: leave the right edge, turn once, arrive at the left edge.
  const mid = (ax + bx) / 2;
  const sweep = b.y > a.y ? 1 : 0;
  const r = 12;
  const dir = b.y > a.y ? 1 : -1;
  return [
    `M ${ax} ${a.y}`,
    `L ${mid - r} ${a.y}`,
    `A ${r} ${r} 0 0 ${sweep} ${mid} ${a.y + r * dir}`,
    `L ${mid} ${b.y - r * dir}`,
    `A ${r} ${r} 0 0 ${sweep === 1 ? 0 : 1} ${mid + r} ${b.y}`,
    `L ${bx} ${b.y}`,
  ].join(" ");
}

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export default function AgentGraph() {
  const reduced = useRef(prefersReducedMotion());
  const [step, setStep] = useState(reduced.current ? WALK.length - 1 : 0);

  useEffect(() => {
    if (reduced.current) return undefined;
    const t = setTimeout(
      () => setStep((s) => (s + 1) % (WALK.length + 2)),
      step === 0 ? 900 : 1100
    );
    return () => clearTimeout(t);
  }, [step]);

  const activeIndex = Math.min(step, WALK.length - 1);
  const active = WALK[activeIndex];
  const reached = new Set(WALK.slice(0, activeIndex + 1));

  return (
    <figure className="agraph">
      <svg
        viewBox="0 0 880 300"
        role="img"
        aria-label="The agent's control flow: detect, diagnose, plan, then execute, halt or escalate, monitor, and report."
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <marker
            id="ag-arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" className="agraph-arrowhead" />
          </marker>
        </defs>

        {EDGES.map((e) => (
          <path
            key={`${e.from}-${e.to}`}
            d={edgePath(e.from, e.to)}
            className={`agraph-edge ${e.kind === "branch" ? "agraph-edge-branch" : ""} ${
              reached.has(e.from) && reached.has(e.to) ? "agraph-edge-lit" : ""
            }`}
            markerEnd="url(#ag-arrow)"
            fill="none"
          />
        ))}

        {/* The retry loop: monitor sends the payment back to the planner. */}
        <path
          d={`M ${N.monitor.x} ${N.monitor.y + H / 2} L ${N.monitor.x} 285
              L ${N.plan.x} 285 L ${N.plan.x} ${N.plan.y + H / 2}`}
          className="agraph-edge agraph-edge-loop"
          markerEnd="url(#ag-arrow)"
          fill="none"
        />
        <text x={(N.monitor.x + N.plan.x) / 2} y={279} className="agraph-loop-label">
          not recovered · retry window scheduled
        </text>

        {Object.entries(N).map(([key, n]) => (
          <g
            key={key}
            className={`agraph-node ${n.tone ? `agraph-node-${n.tone}` : ""} ${
              n.llm ? "agraph-node-llm" : ""
            } ${active === key ? "agraph-node-active" : ""} ${
              reached.has(key) ? "agraph-node-reached" : ""
            }`}
          >
            <rect x={n.x - W / 2} y={n.y - H / 2} width={W} height={H} />
            <text x={n.x} y={n.y - 3} className="agraph-label">
              {n.label}
            </text>
            <text x={n.x} y={n.y + 13} className="agraph-sub">
              {n.sub}
            </text>
          </g>
        ))}

        <text x={N.plan.x + 74} y={104} className="agraph-branch-label">
          stopping rule
        </text>
        <text x={N.plan.x + 74} y={205} className="agraph-branch-label">
          threshold crossed
        </text>
      </svg>

      <figcaption className="agraph-legend">
        <span>
          <i className="agraph-key agraph-key-llm" /> one LLM call, here only
        </span>
        <span>
          <i className="agraph-key agraph-key-plain" /> deterministic
        </span>
        <span>
          <i className="agraph-key agraph-key-stop" /> the agent stops itself
        </span>
      </figcaption>
    </figure>
  );
}
