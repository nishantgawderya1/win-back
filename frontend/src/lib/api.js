// Typed fetch wrappers for the backend routes.
const BASE = "";

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export const api = {
  uploadBatch: async (file) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/batch/upload`, { method: "POST", body: form });
    if (!res.ok) throw new Error(`upload -> ${res.status}`);
    return res.json();
  },
  batchStatus: (id) => get(`/batch/${id}/status`),
  batchResults: (id) => get(`/batch/${id}/results`),
  summary: (id) => get(`/reports/${id}/summary`),
  exceptions: (id) => get(`/reports/${id}/exceptions`),
  halted: (id) => get(`/halted/${id}`),
  auditExportUrl: (id) => `${BASE}/audit/${id}/export`,
};
