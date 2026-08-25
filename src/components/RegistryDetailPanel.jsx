import { X, Loader2, AlertTriangle, RefreshCw, SearchX, ShieldQuestion, ArrowRight, TriangleAlert } from "lucide-react";
import Badge from "./Badge";
import EmptyState from "./EmptyState";
import {
  registryStatusTone,
  escalationStatusTone,
  escalationPriorityTone,
  formatDateTimeMDY,
} from "../utils/registryStatus";
import "./RmdDetailPanel.css";

const ESCALATION_STATUS_OPTIONS = [
  { value: "open", label: "Open" },
  { value: "in_review", label: "In Review" },
  { value: "resolved", label: "Resolved" },
  { value: "rejected", label: "Rejected" },
];

function Field({ label, value }) {
  return (
    <div className="rmd-detail__field">
      <span className="rmd-detail__field-label">{label}</span>
      <span className="rmd-detail__field-value">{value ?? "—"}</span>
    </div>
  );
}

export default function RegistryDetailPanel({
  open,
  loading,
  error,
  record,
  checking,
  onClose,
  onCheckNow,
  onViewCustomer,
  onEscalate,
  onUpdateEscalationStatus,
  updatingEscalation,
}) {
  if (!open) return null;

  const escalation = record?.latest_escalation ?? null;
  const hasActiveEscalation = Boolean(record?.active_escalation);

  return (
    <div className="rmd-detail-overlay" onClick={onClose}>
      <div className="rmd-detail" onClick={(e) => e.stopPropagation()}>
        <div className="rmd-detail__header">
          <div>
            <span className="rmd-detail__eyebrow">Intermediate Registry</span>
            <h3>{record?.registry_id ?? "Registry record"}</h3>
          </div>
          <button type="button" className="rmd-detail__close" onClick={onClose} aria-label="Close details">
            <X size={18} />
          </button>
        </div>

        <div className="rmd-detail__body">
          {loading && (
            <div className="rmd-detail__state">
              <Loader2 size={22} className="rmd-detail__spinner" />
              <span>Loading registry record...</span>
            </div>
          )}

          {!loading && error && (
            <div className="rmd-detail__state rmd-detail__state--error">
              <AlertTriangle size={22} />
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && record && (
            <>
              <div className="rmd-detail__status-row">
                <Badge tone={registryStatusTone(record.status)}>{record.status_label}</Badge>{" "}
                <Badge tone={record.change_detected ? "warning" : "neutral"}>
                  {record.change_detected ? "Changed" : "No Change"}
                </Badge>
              </div>

              <section className="rmd-detail__section">
                <h4>Customer Information</h4>
                <div className="rmd-detail__grid">
                  <Field label="Customer/Vendor Name" value={record.customer_name} />
                  <Field label="Last Checked" value={formatDateTimeMDY(record.last_checked)} />
                </div>
              </section>

              {record.change_detected && record.changes?.length > 0 && (
                <section className="rmd-detail__section">
                  <h4>What Changed Since the Previous Check</h4>
                  <div className="registry-changes">
                    {record.changes.map((change, index) => (
                      <div key={index} className="registry-changes__row">
                        <span className="registry-changes__field">{change.field}</span>
                        <span className="registry-changes__diff">
                          {change.previous} <ArrowRight size={12} /> {change.current}
                        </span>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {record.status === "present" && (
                <>
                  <section className="rmd-detail__section">
                    <h4>Registry Information</h4>
                    <div className="rmd-detail__grid">
                      <Field label="Business Name" value={record.business_name} />
                    </div>
                    <Field label="Business Address" value={record.business_address} />
                  </section>

                  <section className="rmd-detail__section">
                    <h4>Regulatory Contact</h4>
                    <div className="rmd-detail__grid">
                      <Field label="Regulatory Contact Name" value={record.regulatory_contact_name} />
                      <Field label="Regulatory Contact Title" value={record.regulatory_contact_title} />
                      <Field label="Regulatory Contact Telephone" value={record.regulatory_contact_telephone} />
                      <Field label="Regulatory Contact Email" value={record.regulatory_contact_email} />
                    </div>
                  </section>
                </>
              )}

              {record.status === "not_present" && (
                <section className="rmd-detail__section">
                  <EmptyState
                    icon={SearchX}
                    title="Not found"
                    description="This customer was not found in the Intermediate Provider Registry."
                  />
                </section>
              )}

              {record.status === "review_required" && (
                <section className="rmd-detail__section">
                  <EmptyState
                    icon={ShieldQuestion}
                    title="Review required"
                    description="Multiple possible registry records were found. Review is required before confirming a match."
                  />
                  {record.review_candidates?.length > 0 && (
                    <ul className="registry-candidates">
                      {record.review_candidates.map((name, index) => (
                        <li key={index} className="registry-candidates__item">
                          {name}
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              )}

              <section className="rmd-detail__section">
                <h4>Escalation</h4>
                {escalation ? (
                  <>
                    <div className="rmd-detail__field" style={{ marginBottom: 10 }}>
                      <span className="rmd-detail__field-label">Escalation Status</span>
                      <Badge tone={escalationStatusTone(escalation.status)}>{escalation.status_label}</Badge>
                    </div>
                    <div className="rmd-detail__grid">
                      <div className="rmd-detail__field">
                        <span className="rmd-detail__field-label">Priority</span>
                        <Badge tone={escalationPriorityTone(escalation.priority)}>{escalation.priority_label}</Badge>
                      </div>
                      <Field label="Assigned To" value={escalation.assigned_to} />
                      <Field label="Created" value={formatDateTimeMDY(escalation.created_at)} />
                      <Field label="Issue" value={escalation.issue} />
                    </div>
                    {escalation.notes && <Field label="Notes" value={escalation.notes} />}

                    <div className="ticket-form__field" style={{ marginTop: 12 }}>
                      <label htmlFor="esc-status-update">Change Status</label>
                      <select
                        id="esc-status-update"
                        value={escalation.status}
                        disabled={updatingEscalation}
                        onChange={(e) => onUpdateEscalationStatus(escalation, e.target.value)}
                      >
                        {ESCALATION_STATUS_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </>
                ) : (
                  <span className="rmd-detail__field-value">No escalation created</span>
                )}
              </section>

              <div className="rmd-detail__actions">
                <button type="button" className="rmd-detail__action-btn" onClick={() => onViewCustomer(record)}>
                  View Customer
                </button>
                <button
                  type="button"
                  className="rmd-detail__action-btn rmd-detail__action-btn--primary"
                  onClick={() => onCheckNow(record)}
                  disabled={checking}
                >
                  {checking ? <Loader2 size={14} className="rmd-detail__spinner" /> : <RefreshCw size={14} />}
                  {checking ? "Checking..." : "Check Now"}
                </button>
                {record.escalatable && !hasActiveEscalation && (
                  <button
                    type="button"
                    className="rmd-detail__action-btn rmd-detail__action-btn--primary"
                    onClick={() => onEscalate(record)}
                  >
                    <TriangleAlert size={14} />
                    Escalate
                  </button>
                )}
                {record.escalatable && hasActiveEscalation && (
                  <button type="button" className="rmd-detail__action-btn" disabled>
                    <TriangleAlert size={14} />
                    Escalation Open
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
