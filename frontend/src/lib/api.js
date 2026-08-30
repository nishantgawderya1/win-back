// Typed fetch wrappers for the backend routes.
// Everything server-side is namespaced under /api so the client router can own
// the bare product paths (/batch, /audit, /halted, /settings).
import { getAccessToken } from "./supabase.js";

const BASE = "/api";

/** Bearer header when signed in; empty when auth is not configured. */
async function authHeaders() {
  const token = await getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const qs = (params = {}) => {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== ""
  );
  return entries.length ? `?${new URLSearchParams(entries)}` : "";
};

async function get(path) {
  const res = await fetch(`${BASE}${path}`, { headers: await authHeaders() });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

async function send(path, method, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${path} -> ${res.status} ${detail}`);
  }
  return res.json();
}

export const api = {
  health: () => get("/health"),

  // --- Batches ---
  uploadBatch: async (file) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/batch/upload`, {
      method: "POST",
      body: form,
      headers: await authHeaders(),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      throw new Error(`Upload failed (${res.status}). ${detail}`);
    }
    return res.json();
  },
  batches: (limit = 25) => get(`/batches${qs({ limit })}`),
  batchStatus: (id) => get(`/batch/${id}/status`),
  batchResults: (id) => get(`/batch/${id}/results`),
  summary: (id) => get(`/reports/${id}/summary`),

  // --- Global product screens (optional batch_id filter) ---
  audit: (filters = {}) => get(`/audit${qs(filters)}`),
  halted: (filters = {}) => get(`/halted${qs(filters)}`),
  exceptions: (filters = {}) => get(`/exceptions${qs(filters)}`),
  payment: (id) => get(`/payments/${id}`),
  auditExportUrl: (batchId) => `${BASE}/audit/${batchId}/export`,

  // --- Settings ---
  getRules: () => get("/settings/rules"),
  saveRules: (rules) => send("/settings/rules", "PUT", rules),
  connection: () => get("/settings/connection"),
};
