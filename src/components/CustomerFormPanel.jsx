import { useEffect, useState } from "react";
import { X, Loader2 } from "lucide-react";
import { createCustomer } from "../api/customers";
import "./RmdDetailPanel.css";
import "./TicketFormPanel.css";

// Carrier is the only real field on the Customer model -- Country and
// Provider are intentionally never stored there (see
// backend/customers/models.py), so there's nothing else to collect here.
export default function CustomerFormPanel({ open, onClose, onSaved }) {
  const [carrier, setCarrier] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);

  useEffect(() => {
    if (!open) return;
    setCarrier("");
    setFormError(null);
  }, [open]);

  if (!open) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    setFormError(null);

    const trimmed = carrier.trim();
    if (!trimmed) {
      setFormError("Carrier name is required.");
      return;
    }

    setSaving(true);
    createCustomer(trimmed)
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
            <span className="rmd-detail__eyebrow">New Customer</span>
            <h3>Create Customer</h3>
          </div>
          <button type="button" className="rmd-detail__close" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <form className="rmd-detail__body ticket-form" onSubmit={handleSubmit}>
          <section className="rmd-detail__section">
            <h4>Carrier Information</h4>
            <div className="ticket-form__field">
              <label htmlFor="new-customer-carrier">Carrier Name *</label>
              <input
                id="new-customer-carrier"
                type="text"
                placeholder="e.g. Acme Telecom LLC"
                value={carrier}
                onChange={(e) => setCarrier(e.target.value)}
                autoFocus
              />
              <span className="ticket-form__hint">
                Verified automatically against RMD and FCC once created -- Country and Filer ID are matched, never
                entered manually.
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
              {saving ? "Creating..." : "Create Customer"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
