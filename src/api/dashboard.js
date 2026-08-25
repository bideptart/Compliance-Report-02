import { apiGet, apiPost } from "./client";

export function fetchNeedsAttention(limit = 5) {
  return apiGet("/dashboard/needs-attention/", { limit });
}

export function fetchRecentActivity(limit = 8) {
  return apiGet("/dashboard/recent-activity/", { limit });
}

export function clearRecentActivity() {
  return apiPost("/dashboard/recent-activity/clear/", {});
}
