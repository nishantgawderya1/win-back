/**
 * Scripted agent output for the landing-page hero feed.
 *
 * These blocks mirror the shape of real /ws/feed events — same agents, same
 * ordering, same vocabulary as backend/tools/audit.py emits. They are a
 * faithful representation of agent output, not invented marketing copy: each
 * outcome below is one the pipeline genuinely produces.
 */
export const FEED_BLOCKS = [
  {
    id: "pay_xK8m4q7d2b",
    lines: [
      { at: "09:14:23", agent: "detection", text: "classified", value: "UPI_TIMEOUT" },
      { at: "09:14:24", agent: "diagnosis", text: "root cause", value: "network congestion at 23:40" },
      { at: "09:14:24", agent: "diagnosis", text: "recovery score", value: "0.82" },
      { at: "09:14:25", agent: "planner", text: "retry scheduled", value: "tomorrow 09:00" },
      { at: "09:14:26", agent: "executor", text: "retry_payment", value: "₹1,299 RECOVERED", tone: "recovered" },
    ],
  },
  {
    id: "pay_pN2r7k9c41",
    lines: [
      { at: "09:14:27", agent: "detection", text: "classified", value: "CARD_INSUFFICIENT" },
      { at: "09:14:28", agent: "diagnosis", text: "root cause", value: "insufficient funds pre-salary" },
      { at: "09:14:29", agent: "planner", text: "retry scheduled", value: "1st of next month 09:00" },
      { at: "09:14:30", agent: "executor", text: "sms_hinglish", value: "sent to +9198xxxxxx37", tone: "amber" },
    ],
  },
  {
    id: "pay_8f3464f0a4",
    lines: [
      { at: "09:14:31", agent: "detection", text: "classified", value: "CHECKOUT_ABANDONED" },
      { at: "09:14:32", agent: "planner", text: "stopping rule fired", value: "customer replied STOP", tone: "halted" },
      { at: "09:14:32", agent: "halt", text: "halt_action", value: "ALL OUTREACH HALTED", tone: "halted" },
    ],
  },
  {
    id: "pay_1d1896b246",
    lines: [
      { at: "09:14:33", agent: "detection", text: "classified", value: "CARD_BANK_BLOCK" },
      { at: "09:14:34", agent: "diagnosis", text: "root cause", value: "bank hard-declined the card" },
      { at: "09:14:35", agent: "planner", text: "escalation", value: "retries are pointless", tone: "escalated" },
      { at: "09:14:35", agent: "escalate", text: "escalate_human", value: "₹9,676 → HUMAN REVIEW", tone: "escalated" },
    ],
  },
];
