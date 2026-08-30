import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import LandingFeed from "../components/feed/LandingFeed.jsx";
import stats from "../data/demo-stats.json";
import { inr, label, pct } from "../lib/format.js";

const CAPABILITIES = [
  {
    title: "AI Root Cause Reasoning",
    body:
      "Not just error codes. NVIDIA Nemotron diagnoses why the payment failed in plain English — network congestion, salary timing, card block — and the reasoning is stored on every audit entry. If the model is unreachable the agent falls back to deterministic rules and records that it did.",
  },
  {
    title: "Adaptive Retry Sequencer",
    body:
      "A UPI timeout at 11 PM means retry at 9 AM, not two hours later. Insufficient funds on the 25th means retry on the 1st. Retry timing is computed per failure type, not from a fixed backoff.",
  },
  {
    title: "Hard Stopping Rules",
    body:
      "Max 3 retries. No outreach after the cutoff hour. A 2-hour cooldown between nudges. Customers who reply STOP are never contacted again. Every rule is enforced in the planner before any action executes, and every threshold is configurable.",
  },
  {
    title: "Hinglish Recovery Channel",
    body:
      "Recovery SMS written in Hinglish and templated per failure type — not a generic 'payment failed' blast. A specific, contextual nudge that matches how Indian merchants actually talk to their customers.",
  },
  {
    title: "Full Audit Trail",
    body:
      "Every agent action logged with who acted, what they did, why, and what happened. Exportable as CSV. Built for an external financial auditor, not just an internal dashboard.",
    accent: true,
  },
  {
    title: "Honest Exception Report",
    body:
      "WinBack shows what it could not recover and exactly why — hard bank block, customer opted out, retry limit reached. No cherry-picked success metric.",
    accent: true,
  },
];

const STEPS = [
  {
    n: "01",
    title: "Connect",
    body:
      "Add your Razorpay webhook URL once. Every payment.failed event triggers the agent automatically.",
  },
  {
    n: "02",
    title: "Detect & Diagnose",
    body:
      "WinBack classifies each failure from its Razorpay error code, then reasons about the root cause and scores how likely this customer is to pay.",
  },
  {
    n: "03",
    title: "Recover",
    body:
      "The agent executes one bounded action — retry, payment link, WhatsApp nudge, Hinglish SMS — or halts and escalates to a human.",
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

export default function Landing() {
  const scrolled = useNavScrolled();
  const [menuOpen, setMenuOpen] = useState(false);
  const reasons = stats.exception_reasons || {};
  const usedFallback = stats.diagnosis_source !== "nemotron";

  return (
    <div className="landing">
      <header className={`lnav ${scrolled ? "lnav-scrolled" : ""}`}>
        <div className="lnav-inner">
          <Link to="/" className="wordmark">
            WinBack<span className="wordmark-ai">AI</span>
          </Link>
          <nav className={`lnav-links ${menuOpen ? "lnav-open" : ""}`}>
            <a href="#how" onClick={() => setMenuOpen(false)}>
              How it works
            </a>
            <a href="#capabilities" onClick={() => setMenuOpen(false)}>
              Features
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
            <p className="eyebrow">Razorpay merchants · Revenue recovery</p>
            <h1 className="hero-title">
              Most failed payments are recoverable.
              <br />
              WinBack recovers them.
            </h1>
            <p className="hero-sub">
              An autonomous agent that connects to Razorpay, diagnoses every payment failure by
              root cause, and executes a bounded recovery workflow. With a full audit trail and
              hard stopping rules.
            </p>
            <div className="hero-ctas">
              <Link to="/auth" className="btn btn-ghost-accent btn-lg">
                Connect Razorpay
              </Link>
              <Link to="/auth" className="btn btn-link">
                Run a batch demo →
              </Link>
            </div>
            <p className="hero-meta mono dim">
              {inr(stats.total_recovered)} recovered across {stats.record_count} payments in the
              last demo batch · {pct(stats.recovery_rate)} recovery rate ·{" "}
              {stats.failure_type_count} failure types
            </p>
          </div>
          <div className="hero-visual">
            <LandingFeed />
          </div>
        </section>

        {/* --- Problem --- */}
        <section className="section problem">
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
            A UPI timeout at 11 PM is recoverable. An insufficient-funds decline on the 25th can be
            retried on the 1st. A card bank block needs a different payment method, not a retry.
            Your payment gateway already knows why the payment failed. Nobody is doing anything
            about it.
          </p>
          <p className="footnote mono dim">
            The first two figures are industry estimates. The third is measured from the batch
            captured on {String(stats.captured_at).slice(0, 10)}.
          </p>
        </section>

        {/* --- How it works --- */}
        <section className="section how" id="how">
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
        </section>

        {/* --- Capabilities --- */}
        <section className="section caps" id="capabilities">
          <p className="eyebrow">Capabilities</p>
          <div className="cap-grid">
            {CAPABILITIES.map((c) => (
              <article className={`cap ${c.accent ? "cap-accent" : ""}`} key={c.title}>
                <h3 className="cap-title">{c.title}</h3>
                <p className="cap-body">{c.body}</p>
              </article>
            ))}
          </div>
        </section>

        {/* --- The honest section --- */}
        <section className="section honest">
          <div className="honest-inner">
            <p className="eyebrow">What other tools do not show you</p>
            <h2 className="honest-title">
              Including the {stats.unresolved_count} payments we could not recover.
            </h2>
            <p className="honest-copy">
              WinBack reports everything: what was recovered, what was halted because a stopping
              rule fired, and what escalated to a human because automated retries could not fix it.
            </p>
            <p className="honest-copy">
              Every failed recovery carries its specific reason.{" "}
              {reasons.escalated_to_human ?? 0} escalated to human review — hard bank blocks and
              high-value payments, where retrying is the wrong move.{" "}
              {reasons.stopping_rule_halted ?? 0} halted by a stopping rule, a customer who replied
              STOP. {reasons.retried_without_success ?? 0} attempted without success and deferred
              to their next scheduled window. Of {inr(stats.total_at_risk)} at risk,{" "}
              {inr(stats.total_unrecovered)} remains unrecovered. That is the complete picture.
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
                fallback classifier rather than Nemotron — the configured model had reached end of
                life. The pipeline is real; these numbers are what the rules produced.
              </p>
            )}
          </div>
        </section>

        {/* --- Razorpay integration --- */}
        <section className="section integ">
          <div className="integ-card">
            <div className="integ-row mono">
              <span className="integ-brand">Razorpay</span>
              <span className="integ-link">←→</span>
              <span className="integ-brand accent">WinBack AI</span>
            </div>
            <p className="mono dim integ-meta">Built on Razorpay test-mode APIs</p>
            <p className="mono dim integ-meta">payment.failed · subscription.charged.failed</p>
            <p className="mono dim integ-meta">
              Webhook signature verified (HMAC-SHA256) · Idempotency-keyed retries
            </p>
          </div>
        </section>

        {/* --- Final CTA --- */}
        <section className="section cta">
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
