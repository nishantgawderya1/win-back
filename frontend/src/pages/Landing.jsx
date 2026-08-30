import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Logo from "../components/Logo.jsx";
import LandingFeed from "../components/feed/LandingFeed.jsx";
import AgentGraph from "../components/landing/AgentGraph.jsx";
import ReasoningChain from "../components/landing/ReasoningChain.jsx";
import stats from "../data/demo-stats.json";
import { inr, label, pct } from "../lib/format.js";

const CAPABILITIES = [
  {
    title: "Root cause, not error codes",
    body:
      "NVIDIA Nemotron diagnoses why a payment failed in plain English — network congestion, salary timing, a bank block — and scores how likely this customer is to pay. The reasoning is stored on every audit entry.",
  },
  {
    title: "Adaptive retry sequencer",
    body:
      "A UPI timeout at 11 PM means retry at 9 AM, not two hours later. Insufficient funds on the 25th means retry on the 1st. Timing is computed per failure type, in the merchant's timezone.",
  },
  {
    title: "Hard stopping rules",
    body:
      "Max three attempts. No outreach during quiet hours. A cooldown between nudges. Anyone who replies STOP is never contacted again. Enforced in the planner before any action executes.",
  },
  {
    title: "Hinglish recovery channel",
    body:
      "Recovery SMS written in Hinglish and templated per failure type — not a generic 'payment failed' blast, but a contextual nudge that matches how Indian merchants talk to their customers.",
  },
  {
    title: "Full audit trail",
    body:
      "Every action logged with who acted, what they did, why, and what happened. Exportable as CSV. Built for an external financial auditor, not just an internal dashboard.",
    accent: true,
  },
  {
    title: "Honest exception report",
    body:
      "WinBack shows what it could not recover and exactly why — hard bank block, customer opted out, retry limit reached. No cherry-picked success metric.",
    accent: true,
  },
];

// The bounded-autonomy story: what the agent settles alone, and what it will
// not touch without a person. Both halves matter to a merchant handing over
// access to their payment account.
const AUTONOMY = {
  alone: [
    "Classify the failure and diagnose its root cause",
    "Choose one recovery action from the failure type and customer history",
    "Create a real Razorpay payment link and send the outreach",
    "Schedule the next attempt for the window that suits the failure",
    "Retry, up to the ceiling, and confirm recovery from the gateway",
  ],
  never: [
    "Act on a payment above the high-value threshold",
    "Retry after a hard bank block, where retrying cannot work",
    "Contact anyone who replied STOP, ever again",
    "Send outreach during quiet hours, or inside the cooldown",
    "Attempt a fourth time, whatever the diagnosis says",
  ],
};

const STEPS = [
  {
    n: "01",
    title: "Connect",
    body:
      "Add one webhook URL to Razorpay. Every payment.failed event wakes the agent automatically.",
  },
  {
    n: "02",
    title: "Reason",
    body:
      "The agent classifies the failure, diagnoses the cause, and scores whether this customer is worth pursuing.",
  },
  {
    n: "03",
    title: "Act, or decline to",
    body:
      "It executes one bounded action, schedules the next window, or stops itself and says which rule fired.",
  },
];

function useNavScrolled() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return scrolled;
}

/** Reveals a section once as it scrolls into view. */
function Reveal({ children, className = "" }) {
  const [seen, setSeen] = useState(false);
  const [node, setNode] = useState(null);

  useEffect(() => {
    if (!node || seen) return undefined;
    if (!("IntersectionObserver" in window)) {
      setSeen(true);
      return undefined;
    }
    const io = new IntersectionObserver(
      ([entry]) => entry.isIntersecting && setSeen(true),
      { rootMargin: "-60px" }
    );
    io.observe(node);
    return () => io.disconnect();
  }, [node, seen]);

  return (
    <div ref={setNode} className={`reveal ${seen ? "reveal-in" : ""} ${className}`}>
      {children}
    </div>
  );
}

export default function Landing() {
  const scrolled = useNavScrolled();
  const [menuOpen, setMenuOpen] = useState(false);
  const reasons = stats.exception_reasons || {};
  const ladder = stats.attempt_ladder || {};
  const usedFallback = stats.diagnosis_source !== "nemotron";
  const beyondFirst =
    (Number(ladder["2"]) || 0) + (Number(ladder["3"]) || 0);

  return (
    <div className="landing">
      <header className={`lnav ${scrolled ? "lnav-scrolled" : ""}`}>
        <div className="lnav-inner">
          <Link to="/" className="lnav-brand" aria-label="WinBack.AI home">
            <Logo size={30} />
          </Link>
          <nav className={`lnav-links ${menuOpen ? "lnav-open" : ""}`}>
            <a href="#agent" onClick={() => setMenuOpen(false)}>
              The agent
            </a>
            <a href="#guardrails" onClick={() => setMenuOpen(false)}>
              Guardrails
            </a>
            <a href="#capabilities" onClick={() => setMenuOpen(false)}>
              Capabilities
            </a>
            <Link to="/auth" className="btn btn-ghost-accent">
              Connect Razorpay
            </Link>
          </nav>
          <button
            className="lnav-burger mono"
            aria-expanded={menuOpen}
            aria-label="Toggle navigation"
            onClick={() => setMenuOpen((o) => !o)}
          >
            {menuOpen ? "close" : "menu"}
          </button>
        </div>
      </header>

      <main>
        {/* --- Hero --- */}
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow">
              <span className="eyebrow-dot" />
              Razorpay merchants · Autonomous revenue recovery
            </p>
            <h1 className="hero-title">
              Most failed payments are recoverable.
              <br />
              WinBack recovers them.
            </h1>
            <p className="hero-sub">
              An agent that connects to Razorpay, diagnoses every payment failure by root
              cause, and runs a bounded recovery workflow — retry, payment link, Hinglish
              nudge — across days, not one attempt. With hard stopping rules and a full
              audit trail.
            </p>
            <div className="hero-ctas">
              <Link to="/auth" className="btn btn-primary btn-lg">
                Connect Razorpay
              </Link>
              <Link to="/auth" className="btn btn-link">
                Run a batch demo →
              </Link>
            </div>

            <dl className="hero-stats">
              <div>
                <dt>Recovered</dt>
                <dd className="mono accent">{inr(stats.total_recovered)}</dd>
              </div>
              <div>
                <dt>Recovery rate</dt>
                <dd className="mono">{pct(stats.recovery_rate)}</dd>
              </div>
              <div>
                <dt>Decisions logged</dt>
                <dd className="mono">
                  {Object.values(stats.agent_actions || {}).reduce((a, b) => a + b, 0)}
                </dd>
              </div>
            </dl>
            <p className="hero-note mono dim">
              From one real {stats.record_count}-payment batch, captured{" "}
              {String(stats.captured_at).slice(0, 10)}.
            </p>
          </div>
          <div className="hero-visual">
            <LandingFeed />
          </div>
        </section>

        {/* --- The agent --- */}
        <section className="section agent-section" id="agent">
          <Reveal>
            <p className="eyebrow">The agent</p>
            <h2 className="section-title">
              It is a bounded state machine, not a chatbot with API access.
            </h2>
            <p className="section-lede">
              Every payment walks the same graph. Exactly one node calls a language model —
              the diagnosis — and it only ever returns a root cause and two scores. Which
              action gets taken, and whether one is allowed at all, is decided by
              deterministic code that the model cannot reach.
            </p>
          </Reveal>
          <Reveal>
            <AgentGraph />
          </Reveal>
        </section>

        {/* --- Reasoning --- */}
        <section className="section reason-section">
          <div className="reason-grid">
            <Reveal>
              <p className="eyebrow">Reasoning</p>
              <h2 className="section-title">You can read why it decided.</h2>
              <p className="section-lede">
                The agent does not just label a failure. It reasons about the error code,
                the hour it happened, the amount, and what this customer has done before —
                then commits to a recovery score it can be held to.
              </p>
              <p className="section-lede">
                Every step is written to the audit trail alongside the action it produced,
                so a decision made at 2 AM can be reconstructed months later.
              </p>
              <div className="reason-metrics mono">
                <span>
                  <strong className="accent">
                    {stats.diagnosis_counts?.nemotron_ok ?? 0}
                  </strong>{" "}
                  <span className="dim">of {stats.record_count} diagnosed by the model</span>
                </span>
                <span>
                  <strong className="accent">
                    {stats.diagnosis_counts?.fallback_rules ?? 0}
                  </strong>{" "}
                  <span className="dim">fell back to rules, and said so</span>
                </span>
              </div>
            </Reveal>
            <Reveal>
              <ReasoningChain diagnosis={stats.showcase_diagnosis} />
            </Reveal>
          </div>
        </section>

        {/* --- Persistence --- */}
        <section className="section ladder-section">
          <Reveal>
            <p className="eyebrow">Persistence</p>
            <h2 className="section-title">
              It works a payment for weeks, not for one attempt.
            </h2>
            <p className="section-lede">
              A UPI timeout is retried tomorrow morning. An insufficient-funds decline waits
              for the 1st. The agent schedules the window, sleeps, and picks the payment back
              up when it comes due — re-checking every stopping rule on the way through.
            </p>
          </Reveal>
          <Reveal>
            <div className="ladder">
              {["1", "2", "3"].map((a) => {
                const count = Number(ladder[a]) || 0;
                const max = Math.max(...Object.values(ladder).map(Number), 1);
                return (
                  <div className="ladder-step" key={a}>
                    <div className="ladder-bar-track">
                      <div
                        className="ladder-bar"
                        style={{ height: `${Math.max(6, (count / max) * 100)}%` }}
                      />
                    </div>
                    <div className="ladder-n mono accent">{count}</div>
                    <div className="ladder-label mono">
                      attempt {a}
                      {a === "3" && <span className="dim"> · ceiling</span>}
                    </div>
                  </div>
                );
              })}
              <div className="ladder-copy">
                <p>
                  <strong className="mono accent">{beyondFirst}</strong> of{" "}
                  {stats.record_count} payments were worked past their first attempt. Under a
                  one-shot retry they would all have been written off after one try.
                </p>
                <p className="mono dim">
                  Nothing here is a fixed backoff — each window comes from the failure type.
                </p>
              </div>
            </div>
          </Reveal>
        </section>

        {/* --- Guardrails --- */}
        <section className="section guard-section" id="guardrails">
          <Reveal>
            <p className="eyebrow">Autonomy envelope</p>
            <h2 className="section-title">
              The useful question about an agent is what it will not do.
            </h2>
            <p className="section-lede">
              WinBack holds live payment credentials, so its limits are the feature. These
              are enforced in code, checked before every single action, and configurable in
              the product.
            </p>
          </Reveal>
          <Reveal>
            <div className="guard-grid">
              <div className="guard-col">
                <h3 className="guard-head">
                  <span className="guard-mark guard-mark-yes" aria-hidden="true" />
                  Handles alone
                </h3>
                <ul>
                  {AUTONOMY.alone.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </div>
              <div className="guard-col guard-col-never">
                <h3 className="guard-head">
                  <span className="guard-mark guard-mark-no" aria-hidden="true" />
                  Never, without a human
                </h3>
                <ul>
                  {AUTONOMY.never.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </div>
            </div>
          </Reveal>
        </section>

        {/* --- Problem --- */}
        <section className="section problem">
          <Reveal>
            <p className="eyebrow">Industry context</p>
            <div className="bignums">
              <div className="bignum">
                <div className="bignum-value mono">3–7%</div>
                <div className="bignum-label">of GMV lost to payment failures</div>
              </div>
              <div className="bignum">
                <div className="bignum-value mono">₹12L+</div>
                <div className="bignum-label">median monthly loss, mid-size merchants</div>
              </div>
              <div className="bignum">
                <div className="bignum-value mono">{pct(stats.recovery_rate)}</div>
                <div className="bignum-label">
                  recovered in a real {stats.record_count}-payment WinBack batch
                </div>
              </div>
            </div>
            <p className="problem-copy">
              A UPI timeout at 11 PM is recoverable. An insufficient-funds decline on the
              25th can be retried on the 1st. A card bank block needs a different payment
              method, not a retry. Your gateway already knows why the payment failed. Nobody
              is doing anything about it.
            </p>
            <p className="footnote mono dim">
              The first two figures are industry estimates. The third is measured from the
              batch captured on {String(stats.captured_at).slice(0, 10)}.
            </p>
          </Reveal>
        </section>

        {/* --- How it works --- */}
        <section className="section how">
          <Reveal>
            <p className="eyebrow">How it works</p>
            <div className="steps">
              {STEPS.map((s) => (
                <div className="step" key={s.n}>
                  <span className="step-n mono" aria-hidden="true">
                    {s.n}
                  </span>
                  <div className="step-icon" aria-hidden="true" />
                  <h3 className="step-title">{s.title}</h3>
                  <p className="step-body">{s.body}</p>
                </div>
              ))}
            </div>
          </Reveal>
        </section>

        {/* --- Capabilities --- */}
        <section className="section caps" id="capabilities">
          <Reveal>
            <p className="eyebrow">Capabilities</p>
            <div className="cap-grid">
              {CAPABILITIES.map((c) => (
                <article className={`cap ${c.accent ? "cap-accent" : ""}`} key={c.title}>
                  <h3 className="cap-title">{c.title}</h3>
                  <p className="cap-body">{c.body}</p>
                </article>
              ))}
            </div>
          </Reveal>
        </section>

        {/* --- The honest section --- */}
        <section className="section honest">
          <Reveal className="honest-inner">
            <p className="eyebrow">What other tools don't show you</p>
            <h2 className="honest-title">
              Including the {stats.unresolved_count} payments we could not recover.
            </h2>
            <p className="honest-copy">
              WinBack reports everything: what was recovered, what was halted because a
              stopping rule fired, and what escalated to a human because automated retries
              could not fix it.
            </p>
            <p className="honest-copy">
              Every failed recovery carries its specific reason.{" "}
              {reasons.escalated_to_human ?? 0} escalated to human review — hard bank blocks
              and high-value payments, where retrying is the wrong move.{" "}
              {reasons.stopping_rule_halted ?? 0} halted by a stopping rule, customers who
              replied STOP. {reasons.retried_without_success ?? 0} attempted without success.
              Of {inr(stats.total_at_risk)} at risk, {inr(stats.total_unrecovered)} remains
              unrecovered. That is the complete picture.
            </p>
            <div className="exception-preview">
              <div className="ep-head mono">
                <span>payment_id</span>
                <span>amount</span>
                <span>failure</span>
                <span>reason unresolved</span>
              </div>
              {stats.sample_exceptions.map((e) => (
                <div className="ep-row mono" key={e.payment_id}>
                  <span className="accent">{e.payment_id}</span>
                  <span>{inr(e.amount)}</span>
                  <span className="muted">{label(e.failure_type)}</span>
                  <span className="muted">{e.reason}</span>
                </div>
              ))}
            </div>
            {usedFallback && (
              <p className="footnote mono dim">
                Disclosure: in the captured batch every diagnosis came from the deterministic
                fallback rather than Nemotron — the configured model was unavailable. The
                pipeline is real; these numbers are what the rules produced.
              </p>
            )}
          </Reveal>
        </section>

        {/* --- Razorpay integration --- */}
        <section className="section integ">
          <Reveal>
            <div className="integ-card">
              <div className="integ-row mono">
                <span className="integ-brand">Razorpay</span>
                <span className="integ-link">←→</span>
                <span className="integ-brand accent">WinBack AI</span>
              </div>
              <p className="mono dim integ-meta">Built on Razorpay test-mode APIs</p>
              <p className="mono dim integ-meta">
                payment.failed · payment_link.paid · subscription.charged.failed
              </p>
              <p className="mono dim integ-meta">
                Real payment links · HMAC-SHA256 verified webhooks · idempotency-keyed
                attempts
              </p>
            </div>
          </Reveal>
        </section>

        {/* --- Final CTA --- */}
        <section className="section cta">
          <Reveal>
            <h2 className="cta-title">
              Connect your Razorpay account.
              <br />
              Run the first batch.
            </h2>
            <Link to="/auth" className="btn btn-primary btn-lg">
              Connect Razorpay →
            </Link>
            <p className="mono dim cta-note">
              Test-mode only. No real money. Full audit trail from minute one.
            </p>
          </Reveal>
        </section>
      </main>

      <footer className="lfooter">
        <span className="mono dim">WinBack AI · Razorpay Buildathon 2026 · Track 03</span>
        <a className="mono dim" href="https://github.com/nishantgawderya1/win-back">
          GitHub
        </a>
      </footer>
    </div>
  );
}
