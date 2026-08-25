export const TICKET_STATUS_BADGE = {
  open: { tone: "danger" },
  in_progress: { tone: "warning" },
  resolved: { tone: "success" },
  closed: { tone: "neutral" },
};

export function ticketStatusTone(status) {
  return TICKET_STATUS_BADGE[status]?.tone ?? "neutral";
}

// Displayed as MM/DD/YYYY, never DD/MM/YYYY -- built directly from the
// unambiguous "YYYY-MM-DD" string the API sends, so there's no Date-object
// timezone shifting involved (same approach as utils/agreementStatus.js).
export function formatDateMDY(isoDate) {
  if (!isoDate) return "—";
  const [year, month, day] = isoDate.split("-");
  if (!year || !month || !day) return isoDate;
  return `${month}/${day}/${year}`;
}
