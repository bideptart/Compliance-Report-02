import { useEffect, useMemo, useState } from "react";
import { X, Loader2 } from "lucide-react";
import { createAgreement, updateAgreement, renewAgreement } from "../api/agreements";
import "./RmdDetailPanel.css";
import "./AgreementFormPanel.css";

const AGREEMENT_TYPE_OPTIONS = [
  { value: "customer_agreement", label: "Customer Agreement" },
  { value: "carrier_agreement", label: "Carrier Agreement" },
  { value: "service_agreement", label: "Service Agreement" },
  { value: "compliance_agreement", label: "Compliance Agreement" },
  { value: "other", label: "Other" },
];

const STATUS_OPTIONS = [
  { value: "draft", label: "Draft" },
  { value: "pending_review", label: "Pending Review" },
  { value: "active", label: "Active" },
  { value: "terminated", label: "Terminated" },
];

const MODE_META = {
  create: { eyebrow: "New Agreement", title: "Create Agreement", submitLabel: "Save Agreement" },
  edit: { eyebrow: "Edit Agreement", title: "Edit Agreement", submitLabel: "Save Changes" },
  renew: { eyebrow: "Renew Agreement", title: "Renew Agreement", submitLabel: "Create Renewal" },
};

export default function AgreementFormPanel({ open, mode, agreement, customers, lockedCustomer, onClose, onSaved }) {
  const [customerInput, setCustomerInput] = useState("");
  const [agreementTitle, setAgreementTitle] = useState("");
  const [agreementType, setAgreementType] = useState("customer_agreement");
  const [status, setStatus] = useState("draft");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [autoRenewal, setAutoRenewal] = useState(false);
  const [document, setDocument] = useState(null);
  const [notes, setNotes] = useState("");

  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);

  useEffect(() => {
    if (!open) return;

    if ((mode === "edit" || mode === "renew") && agreement) {
      setCustomerInput(agreement.customer_name || "");
      setAgreementTitle(agreement.agreement_title || "");
      setAgreementType(agreement.agreement_type || "customer_agreement");
      setStatus(mode === "edit" ? agreement.status : "draft");
      setEffectiveDate(mode === "renew" ? "" : agreement.effective_date || "");
      setExpiryDate(mode === "renew" ? "" : agreement.expiry_date || "");
      setAutoRenewal(Boolean(agreement.auto_renewal));
      setNotes(agreement.notes || "");
    } else {
      setCustomerInput(lockedCustomer ? lockedCustomer.company_name || lockedCustomer.carrier : "");
      setAgreementTitle("");
      setAgreementType("customer_agreement");
      setStatus("draft");
      setEffectiveDate("");
      setExpiryDate("");
      setAutoRenewal(false);
      setNotes("");
    }
    setDocument(null);
    setFormError(null);
  }, [open, mode, agreement, lockedCustomer]);

  const customerIdByLabel = useMemo(() => {
    const map = new Map();
    customers.forEach((c) => map.set((c.company_name || c.carrier).trim().toLowerCase(), c.id));
    return map;
  }, [customers]);

  const resolvedCustomerId =
    mode === "create"
      ? lockedCustomer?.id ?? customerIdByLabel.get(customerInput.trim().toLowerCase())
      : agreement?.customer;

  if (!open) return null;

  const meta = MODE_META[mode];

  const handleSubmit = (e) => {
    e.preventDefault();
    setFormError(null);

    if (mode === "create" && !resolvedCustomerId) {
      setFormError("Select a real customer from the list.");
      return;
    }
    if (!agreementTitle.trim()) {
      setFormError("Agreement title is required.");
      return;
    }
    if (!effectiveDate) {
      setFormError("Effective date is required.");
      return;
    }

    setSaving(true);

    let request;
    if (mode === "create") {
      request = createAgreement({
        customerId: resolvedCustomerId,
        agreementTitle: agreementTitle.trim(),
        agreementType,
        status,
        effectiveDate,
        expiryDate,
        autoRenewal,
        document,
        notes,
      });
    } else if (mode === "edit") {
      request = updateAgreement(agreement.id, {
        agreementTitle: agreementTitle.trim(),
        agreementType,
        status,
        effectiveDate,
        expiryDate,
        autoRenewal,
        document,
        notes,
      });
    } else {
      request = renewAgreement(agreement.id, {
        agreementTitle: agreementTitle.trim(),
        agreementType,
        effectiveDate,
        expiryDate,
        autoRenewal,
        document,
        notes,
      });
    }

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
      <div className="rmd-detail agreement-form-panel" onClick={(e) => e.stopPropagation()}>
        <div className="rmd-detail__header">
          <div>
            <span className="rmd-detail__eyebrow">{meta.eyebrow}</span>
            <h3>{meta.title}</h3>
          </div>
          <button type="button" className="rmd-detail__close" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <form className="rmd-detail__body agreement-form" onSubmit={handleSubmit}>
          <section className="rmd-detail__section">
            <h4>Customer Information</h4>
            <div className="agreement-form__field">
              <label htmlFor="agr-customer">Customer *</label>
              {mode === "create" && !lockedCustomer ? (
                <>
                  <input
                    id="agr-customer"
                    type="text"
                    list="agr-customer-options"
                    placeholder="Search or select a customer..."
                    value={customerInput}
                    onChange={(e) => setCustomerInput(e.target.value)}
                    autoComplete="off"
                  />
                  <datalist id="agr-customer-options">
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
            <h4>Agreement Information</h4>
            {mode !== "create" && agreement && (
              <div className="agreement-form__field">
                <label>Agreement ID</label>
                <input type="text" value={agreement.agreement_id} disabled />
              </div>
            )}
            {mode === "create" && (
              <div className="agreement-form__field">
                <label>Agreement ID</label>
                <input type="text" value="Automatically generated (e.g. AGR-0001)" disabled />
              </div>
            )}
            <div className="agreement-form__field">
              <label htmlFor="agr-title">Agreement Title *</label>
              <input
                id="agr-title"
                type="text"
                placeholder="e.g. Master Service Agreement"
                value={agreementTitle}
                onChange={(e) => setAgreementTitle(e.target.value)}
              />
            </div>
            <div className="agreement-form__row">
              <div className="agreement-form__field">
                <label htmlFor="agr-type">Agreement Type *</label>
                <select id="agr-type" value={agreementType} onChange={(e) => setAgreementType(e.target.value)}>
                  {AGREEMENT_TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              {mode !== "renew" && (
                <div className="agreement-form__field">
                  <label htmlFor="agr-status">Status *</label>
                  <select id="agr-status" value={status} onChange={(e) => setStatus(e.target.value)}>
                    {STATUS_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          </section>

          <section className="rmd-detail__section">
            <h4>Agreement Dates</h4>
            <div className="agreement-form__row">
              <div className="agreement-form__field">
                <label htmlFor="agr-effective">Effective Date * (MM/DD/YYYY)</label>
                <input id="agr-effective" type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} />
              </div>
              <div className="agreement-form__field">
                <label htmlFor="agr-expiry">Expiry Date (MM/DD/YYYY)</label>
                <input id="agr-expiry" type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
              </div>
            </div>
            <div className="agreement-form__field">
              <label>Auto Renewal</label>
              <div className="agreement-form__radio-group">
                <label className="agreement-form__radio">
                  <input type="radio" checked={autoRenewal === true} onChange={() => setAutoRenewal(true)} />
                  Yes
                </label>
                <label className="agreement-form__radio">
                  <input type="radio" checked={autoRenewal === false} onChange={() => setAutoRenewal(false)} />
                  No
                </label>
              </div>
            </div>
          </section>

          <section className="rmd-detail__section">
            <h4>Agreement Document</h4>
            <div className="agreement-form__field">
              <label htmlFor="agr-document">
                {mode === "renew" ? "Upload New Document (optional)" : "Choose File (PDF, DOC, DOCX)"}
              </label>
              <input
                id="agr-document"
                type="file"
                accept=".pdf,.doc,.docx"
                onChange={(e) => setDocument(e.target.files?.[0] ?? null)}
              />
              {mode === "edit" && agreement?.document_name && !document && (
                <span className="agreement-form__hint">Current file: {agreement.document_name}</span>
              )}
            </div>
          </section>

          <section className="rmd-detail__section">
            <h4>Additional Information</h4>
            <div className="agreement-form__field">
              <label htmlFor="agr-notes">Notes</label>
              <textarea
                id="agr-notes"
                rows={3}
                placeholder="Optional notes about this agreement..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          </section>

          {formError && <p className="agreement-form__error">{formError}</p>}

          <div className="agreement-form__actions">
            <button type="button" className="agreement-form__cancel" onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button type="submit" className="agreement-form__submit" disabled={saving}>
              {saving && <Loader2 size={15} className="agreement-form__spinner" />}
              {saving ? "Saving..." : meta.submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
