import { useEffect, useState } from "react";
import { X, Loader2 } from "lucide-react";
import { createEscalation } from "../api/intermediateRegistry";
import "./RmdDetailPanel.css";
import "./TicketFormPanel.css";

const PRIORITY_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

function todayDisplay() {
  return new Date().toLocaleDateString("en-US", { dateStyle: "medium" });
}

// Creates a real escalation for one Intermediate Registry check -- see
// api/intermediateRegistry.createEscalation. Company Name, Customer ID,
// Check Type, and Escalation Status are never user-editable here; they
// always come from the real registry record being escalated (record
// prop), the same way the backend itself derives them, so an escalation
// can never end up linked to the wrong company.
export default function EscalationFormPanel({ open, record, onClose, onCreated }) {
  const [issue, setIssue] = useState("");
  const [priority, setPriority] = useState("medium");
  const [assignedTo, setAssignedTo] = useState("");
  const [notes, setNotes] = useState("");

  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);

  useEffect(() => {
    if (!open) return;
    setIssue("");
    setPriority("medium");
    setAssignedTo("");
    setNotes("");
    setFormError(null);
  }, [open, record]);

  if (!open || !record) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    setFormError(null);

    if (!issue.trim()) {
      setFormError("Issue / Reason is required.");
      return;
    }

    setSaving(true);
    createEscalation(record.id, {
      issue: issue.trim(),
      priority,
      assigned_to: assignedTo.trim() || undefined,
      notes: notes.trim() || undefined,
    })
      .then((escalation) => {
        setSaving(false);
        onCreated(escalation);
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
            <span className="rmd-detail__eyebrow">New Escalation</span>
            <h3>Create Escalation</h3>
          </div>
          <button type="button" className="rmd-detail__close" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <form className="rmd-detail__body ticket-form" onSubmit={handleSubmit}>
          <section className="rmd-detail__section">
            <h4>Registry Check</h4>
            <div className="ticket-form__row">
              <div className="ticket-form__field">
                <label>Company Name</label>
                <input type="text" value={record.customer_name || ""} disabled />
              </div>
              <div className="ticket-form__field">
                <label>Customer ID</label>
                <input type="text" value={record.customer ?? ""} disabled />
              </div>
            </div>
            <div className="ticket-form__row">
              <div className="ticket-form__field">
                <label>Check Type</label>
                <input type="text" value="Intermediate Registry" disabled />
              </div>
              <div className="ticket-form__field">
                <label>Verification Result</label>
                <input type="text" value={record.status_label || ""} disabled />
              </div>
            </div>
          </section>

          <section className="rmd-detail__section">
            <h4>Escalation Details</h4>
            <div className="ticket-form__field">
              <label htmlFor="esc-issue">Issue / Reason *</label>
              <textarea
                id="esc-issue"
                rows={3}
                placeholder="Describe why this needs to be escalated..."
                value={issue}
                onChange={(e) => setIssue(e.target.value)}
              />
            </div>

            <div className="ticket-form__row">
              <div className="ticket-form__field">
                <label htmlFor="esc-priority">Priority *</label>
                <select id="esc-priority" value={priority} onChange={(e) => setPriority(e.target.value)}>
                  {PRIORITY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="ticket-form__field">
                <label htmlFor="esc-assigned">Assigned To</label>
                <input
                  id="esc-assigned"
                  type="text"
                  placeholder="e.g. Compliance Team"
                  value={assignedTo}
                  onChange={(e) => setAssignedTo(e.target.value)}
                />
              </div>
            </div>

            <div className="ticket-form__field">
              <label htmlFor="esc-notes">Description / Notes</label>
              <textarea
                id="esc-notes"
                rows={3}
                placeholder="Optional additional context..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>

            <div className="ticket-form__row">
              <div className="ticket-form__field">
                <label>Escalation Status</label>
                <input type="text" value="Open" disabled />
              </div>
              <div className="ticket-form__field">
                <label>Created Date</label>
                <input type="text" value={todayDisplay()} disabled />
              </div>
            </div>
          </section>

          {formError && <p className="ticket-form__error">{formError}</p>}

          <div className="ticket-form__actions">
            <button type="button" className="ticket-form__cancel" onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button type="submit" className="ticket-form__submit" disabled={saving}>
              {saving && <Loader2 size={15} className="ticket-form__spinner" />}
              {saving ? "Creating..." : "Create Escalation"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
