// Formatting helpers. Every number rendered through these belongs in mono.

export const inr = (n) =>
  `₹${Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

// Compact form for headline metrics: ₹19.5L, ₹1.2Cr.
export function inrCompact(n) {
  const v = Number(n || 0);
  if (v >= 1e7) return `₹${(v / 1e7).toFixed(2)}Cr`;
  if (v >= 1e5) return `₹${(v / 1e5).toFixed(2)}L`;
  if (v >= 1e3) return `₹${(v / 1e3).toFixed(1)}K`;
  return `₹${v.toFixed(0)}`;
}

export const pct = (r, digits = 1) => `${((r || 0) * 100).toFixed(digits)}%`;

export const time = (ts) => {
  if (!ts) return "";
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleTimeString("en-IN", { hour12: false });
};

export const dateTime = (ts) => {
  if (!ts) return "";
  const d = new Date(ts);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleString("en-IN", { hour12: false, dateStyle: "medium", timeStyle: "short" });
};

// upi_timeout -> UPI TIMEOUT
export const label = (s) => (s || "unknown").replace(/_/g, " ").toUpperCase();

export const truncate = (s, n = 90) =>
  !s ? "" : s.length <= n ? s : `${s.slice(0, n - 1)}…`;
