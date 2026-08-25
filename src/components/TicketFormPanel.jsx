import { useEffect, useMemo, useState } from "react";
import { X, Loader2 } from "lucide-react";
import { createTicket, updateTicket } from "../api/tickets";
import "./RmdDetailPanel.css";
import "./TicketFormPanel.css";

const STATUS_OPTIONS = [
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In Progress" },
  { value: "resolved", label: "Resolved" },
  { value: "closed", label: "Closed" },
];

function todayIso() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

const MODE_META = {
  create: { eyebrow: "New Ticket", title: "Create Trouble Ticket", submitLabel: "Create Ticket" },
  edit: { eyebrow: "Edit Ticket", title: "Edit Trouble Ticket", submitLabel: "Save Changes" },
};

export default function TicketFormPanel({ open, mode, ticket, customers, onClose, onSaved }) {
  const [customerInput, setCustomerInput] = useState("");
  const [dateOpened, setDateOpened] = useState(todayIso());
  const [problem, setProblem] = useState("");
  const [status, setStatus] = useState("open");
  const [nocNotified, setNocNotified] = useState(false);
  const [customerNotified, setCustomerNotified] = useState(false);
  const [resolutionComments, setResolutionComments] = useState("");
  const [dateClosed, setDateClosed] = useState("");

  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);

  useEffect(() => {
    if (!open) return;

    if (mode === "edit" && ticket) {
      setCustomerInput(ticket.customer_name || "");
      setDateOpened(ticket.date_opened || todayIso());
      setProblem(ticket.problem || "");
      setStatus(ticket.status || "open");
      setNocNotified(Boolean(ticket.noc_notified));
      setCustomerNotified(Boolean(ticket.customer_notified));
      setResolutionComments(ticket.resolution_comments || "");
      setDateClosed(ticket.date_closed || "");
    } else {
      setCustomerInput("");
      setDateOpened(todayIso());
      setProblem("");
      setStatus("open");
      setNocNotified(false);
      setCustomerNotified(false);
      setResolutionComments("");
      setDateClosed("");
    }
    setFormError(null);
  }, [open, mode, ticket]);

  const customerIdByLabel = useMemo(() => {
    const map = new Map();
    customers.forEach((c) => map.set((c.company_name || c.carrier).trim().toLowerCase(), c.id));
    return map;
  }, [customers]);

  const resolvedCustomerId =
    mode === "create" ? customerIdByLabel.get(customerInput.trim().toLowerCase()) : ticket?.customer;

  if (!open) return null;

  const meta = MODE_META[mode];

  const handleSubmit = (e) => {
    e.preventDefault();
    setFormError(null);

    if (mode === "create" && !resolvedCustomerId) {
      setFormError("Select a real customer from the list.");
      return;
    }
    if (!dateOpened) {
      setFormError("Date Opened is required.");
      return;
    }
    if (!problem.trim()) {
      setFormError("Problem description is required.");
      return;
    }
    if (status === "closed" && !dateClosed) {
      setFormError("Date Closed is required when status is Closed.");
      return;
    }

    const fields = {
      date_opened: dateOpened,
      problem: problem.trim(),
      status,
      noc_notified: nocNotified,
      customer_notified: customerNotified,
      resolution_comments: resolutionComments.trim() || null,
      date_closed: dateClosed || null,
    };
    if (mode === "create") fields.customer = resolvedCustomerId;

    setSaving(true);
    const request = mode === "create" ? createTicket(fields) : updateTicket(ticket.id, fields);

    request
      .then((saved) => {
        setSaving(false);
        onSaved(saved);
      })
      .catch((err) => {
        setSaving(false);
        setFormError(err.message || "Something went wrong. Please try again.");
      });
  };

  return (
    <div className="rmd-detail-overlay" onClick={onClose}>
      <div className="rmd-detail ticket-form-panel" onClick={(e) => e.stopPropagation()}>
        <div className="rmd-detail__header">
          <div>
            <span className="rmd-detail__eyebrow">{meta.eyebrow}</span>
            <h3>{meta.title}</h3>
          </div>
          <button type="button" className="rmd-detail__close" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <form className="rmd-detail__body ticket-form" onSubmit={handleSubmit}>
          <section className="rmd-detail__section">
            <h4>Customer</h4>
            <div className="ticket-form__field">
              <label htmlFor="tkt-customer">Customer *</label>
              {mode === "create" ? (
                <>
                  <input
                    id="tkt-customer"
                    type="text"
                    list="tkt-customer-options"
                    placeholder="Search or select a customer..."
                    value={customerInput}
                    onChange={(e) => setCustomerInput(e.target.value)}
                    autoComplete="off"
                  />
                  <datalist id="tkt-customer-options">
                    {customers.map((c) => (
                      <option key={c.id} value={c.company_name || c.carrier} />
                    ))}
                  </datalist>
                </>
              ) : (
                <input type="text" value={customerInput} disabled />
              )}
            </div>
          </section>

          <section className="rmd-detail__section">
            <h4>Ticket Information</h4>
            {mode === "edit" && ticket && (
              <div className="ticket-form__field">
                <label>Ticket Number</label>
                <input type="text" value={ticket.ticket_number} disabled />
              </div>
            )}
            {mode === "create" && (
              <div className="ticket-form__field">
                <label>Ticket Number</label>
                <input type="text" value="Automatically generated (e.g. TT-000001)" disabled />
              </div>
            )}

            <div className="ticket-form__row">
              <div className="ticket-form__field">
                <label htmlFor="tkt-opened">Date Opened * (MM/DD/YYYY)</label>
                <input id="tkt-opened" type="date" value={dateOpened} onChange={(e) => setDateOpened(e.target.value)} />
              </div>
              <div className="ticket-form__field">
                <label htmlFor="tkt-status">Status *</label>
                <select id="tkt-status" value={status} onChange={(e) => setStatus(e.target.value)}>
                  {STATUS_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="ticket-form__field">
              <label htmlFor="tkt-problem">Problem *</label>
              <textarea
                id="tkt-problem"
                rows={3}
                placeholder="Describe the customer issue..."
                value={problem}
                onChange={(e) => setProblem(e.target.value)}
              />
            </div>
          </section>

          <section className="rmd-detail__section">
            <h4>Notifications</h4>
            <div className="ticket-form__row">
              <div className="ticket-form__field">
                <label>NOC Notified? *</label>
                <div className="ticket-form__radio-group">
                  <label className="ticket-form__radio">
                    <input type="radio" checked={nocNotified === true} onChange={() => setNocNotified(true)} />
                    Yes
                  </label>
                  <label className="ticket-form__radio">
                    <input type="radio" checked={nocNotified === false} onChange={() => setNocNotified(false)} />
                    No
                  </label>
                </div>
              </div>
              <div className="ticket-form__field">
                <label>Customer Notified? *</label>
                <div className="ticket-form__radio-group">
                  <label className="ticket-form__radio">
                    <input
                      type="radio"
                      checked={customerNotified === true}
                      onChange={() => setCustomerNotified(true)}
                    />
                    Yes
                  </label>
                  <label className="ticket-form__radio">
                    <input
                      type="radio"
                      checked={customerNotified === false}
                      onChange={() => setCustomerNotified(false)}
                    />
                    No
                  </label>
                </div>
              </div>
            </div>
          </section>

          <section className="rmd-detail__section">
            <h4>Resolution</h4>
            <div className="ticket-form__field">
              <label htmlFor="tkt-resolution">Resolution / Comments</label>
              <textarea
                id="tkt-resolution"
                rows={3}
                placeholder="Optional -- update as the ticket progresses..."
                value={resolutionComments}
                onChange={(e) => setResolutionComments(e.target.value)}
              />
            </div>
            <div className="ticket-form__field">
              <label htmlFor="tkt-closed">Date Closed (MM/DD/YYYY)</label>
              <input id="tkt-closed" type="date" value={dateClosed} onChange={(e) => setDateClosed(e.target.value)} />
              <span className="ticket-form__hint">
                {status === "closed"
                  ? "Required when status is Closed -- left empty, today's date is used automatically."
                  : "Only meaningful once the ticket is Closed."}
              </span>
            </div>
          </section>

          {formError && <p className="ticket-form__error">{formError}</p>}

          <div className="ticket-form__actions">
            <button type="button" className="ticket-form__cancel" onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button type="submit" className="ticket-form__submit" disabled={saving}>
              {saving && <Loader2 size={15} className="ticket-form__spinner" />}
              {saving ? "Saving..." : meta.submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
