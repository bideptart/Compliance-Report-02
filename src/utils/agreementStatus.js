export const AGREEMENT_STATUS_BADGE = {
  draft: { tone: "neutral" },
  pending_review: { tone: "warning" },
  active: { tone: "success" },
  expiring_soon: { tone: "warning" },
  expired: { tone: "danger" },
  terminated: { tone: "neutral" },
};

export function agreementStatusTone(status) {
  return AGREEMENT_STATUS_BADGE[status]?.tone ?? "neutral";
}

// Displayed as MM/DD/YYYY, never DD/MM/YYYY -- built directly from the
// unambiguous "YYYY-MM-DD" string the API sends, so there's no Date-object
// timezone shifting involved.
export function formatDateMDY(isoDate) {
  if (!isoDate) return "—";
  const [year, month, day] = isoDate.split("-");
  if (!year || !month || !day) return isoDate;
  return `${month}/${day}/${year}`;
}

export function formatDateTimeMDY(isoDateTime) {
  if (!isoDateTime) return "—";
  const date = new Date(isoDateTime);
  return date.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
}
