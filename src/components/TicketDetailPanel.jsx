import { X, Loader2, AlertTriangle, Pencil, CheckCircle2 } from "lucide-react";
import Badge from "./Badge";
import { ticketStatusTone, formatDateMDY } from "../utils/ticketStatus";
import "./RmdDetailPanel.css";

function Field({ label, value }) {
  return (
    <div className="rmd-detail__field">
      <span className="rmd-detail__field-label">{label}</span>
      <span className="rmd-detail__field-value">{value ?? "—"}</span>
    </div>
  );
}

const STATUS_LABELS = {
  open: "Open",
  in_progress: "In Progress",
  resolved: "Resolved",
  closed: "Closed",
};

export default function TicketDetailPanel({ open, loading, error, ticket, onClose, onEdit, onCloseTicket }) {
  if (!open) return null;

  return (
    <div className="rmd-detail-overlay" onClick={onClose}>
      <div className="rmd-detail" onClick={(e) => e.stopPropagation()}>
        <div className="rmd-detail__header">
          <div>
            <span className="rmd-detail__eyebrow">Trouble Ticket</span>
            <h3>{ticket?.ticket_number ?? "Ticket details"}</h3>
          </div>
          <button type="button" className="rmd-detail__close" onClick={onClose} aria-label="Close details">
            <X size={18} />
          </button>
        </div>

        <div className="rmd-detail__body">
          {loading && (
            <div className="rmd-detail__state">
              <Loader2 size={22} className="rmd-detail__spinner" />
              <span>Loading ticket details...</span>
            </div>
          )}

          {!loading && error && (
            <div className="rmd-detail__state rmd-detail__state--error">
              <AlertTriangle size={22} />
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && ticket && (
            <>
              <div className="rmd-detail__status-row">
                <Badge tone={ticketStatusTone(ticket.status)}>{STATUS_LABELS[ticket.status] ?? ticket.status}</Badge>
              </div>

              <section className="rmd-detail__section">
                <h4>Customer Information</h4>
                <div className="rmd-detail__grid">
                  <Field label="Company Name" value={ticket.customer_info?.company_name ?? ticket.customer_name} />
                  <Field label="Country of Origin" value={ticket.customer_info?.country} />
                  <Field label="FRN" value={ticket.customer_info?.frn} />
                </div>
              </section>

              <section className="rmd-detail__section">
                <h4>Ticket Information</h4>
                <div className="rmd-detail__grid">
                  <Field label="Ticket Number" value={ticket.ticket_number} />
                  <Field label="Date Opened" value={formatDateMDY(ticket.date_opened)} />
                  <Field label="NOC Notified" value={ticket.noc_notified ? "Yes" : "No"} />
                  <Field label="Customer Notified" value={ticket.customer_notified ? "Yes" : "No"} />
                  <Field label="Date Closed" value={formatDateMDY(ticket.date_closed)} />
                </div>
                <Field label="Problem" value={ticket.problem} />
              </section>

              <section className="rmd-detail__section">
                <h4>Resolution / Comments</h4>
                <Field label="Notes" value={ticket.resolution_comments} />
              </section>

              <div className="rmd-detail__actions">
                <button type="button" className="rmd-detail__action-btn" onClick={() => onEdit(ticket)}>
                  <Pencil size={14} />
                  Edit Ticket
                </button>
                {ticket.status !== "closed" && (
                  <button
                    type="button"
                    className="rmd-detail__action-btn rmd-detail__action-btn--primary"
                    onClick={() => onCloseTicket(ticket)}
                  >
                    <CheckCircle2 size={14} />
                    Close Ticket
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
