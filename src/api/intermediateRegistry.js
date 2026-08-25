import { apiGet, apiPatch, apiPost } from "./client";

export function fetchRegistryStats() {
  return apiGet("/intermediate-registry/stats/");
}

export function fetchRegistryRecords({ page = 1, search, status } = {}) {
  return apiGet("/intermediate-registry/", { page, search, status });
}

export function fetchRegistryDetail(id) {
  return apiGet(`/intermediate-registry/${id}/`);
}

export function runRegistryCheck(id) {
  return apiPost(`/intermediate-registry/${id}/check/`, {});
}

// Creates a real escalation against one registry check -- only ever
// called from an explicit user action (the Escalate button), never
// automatically. The backend rejects this with a 409 if an active
// (Open/In Review) escalation already exists for the same check.
export function createEscalation(recordId, fields) {
  return apiPost(`/intermediate-registry/${recordId}/escalations/`, fields);
}

export function updateEscalation(id, fields) {
  return apiPatch(`/intermediate-registry/escalations/${id}/`, fields);
}
