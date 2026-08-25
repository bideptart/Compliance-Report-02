export const REGISTRY_STATUS_TONE = {
  present: "success",
  not_present: "neutral",
  review_required: "warning",
};

export function registryStatusTone(status) {
  return REGISTRY_STATUS_TONE[status] ?? "neutral";
}

export const ESCALATION_STATUS_TONE = {
  open: "danger",
  in_review: "warning",
  resolved: "success",
  rejected: "neutral",
};

export function escalationStatusTone(status) {
  return ESCALATION_STATUS_TONE[status] ?? "neutral";
}

export const ESCALATION_PRIORITY_TONE = {
  low: "neutral",
  medium: "warning",
  high: "danger",
  critical: "danger",
};

export function escalationPriorityTone(priority) {
  return ESCALATION_PRIORITY_TONE[priority] ?? "neutral";
}

// Displayed as MM/DD/YYYY HH:MM, never DD/MM/YYYY.
export function formatDateTimeMDY(isoDateTime) {
  if (!isoDateTime) return "—";
  const date = new Date(isoDateTime);
  return date.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
}
