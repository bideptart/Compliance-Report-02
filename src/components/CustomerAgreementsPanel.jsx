import { X, ChevronRight, Loader2, FileX2 } from "lucide-react";
import Badge from "./Badge";
import { agreementStatusTone, formatDateMDY } from "../utils/agreementStatus";
import "./RmdDetailPanel.css";
import "./CustomerRecordsPanel.css";

const STATUS_LABELS = {
  draft: "Draft",
  pending_review: "Pending Review",
  active: "Active",
  expiring_soon: "Expiring Soon",
  expired: "Expired",
  terminated: "Terminated",
};

// Same sliding side panel as CustomerRecordsPanel (reuses its CSS classes),
// listing the real agreements a specific customer has -- clicking one opens
// its full AgreementDetailPanel, the same "view the list, then view one
// record" flow Documents/Tech Form/KYC already use.
export default function CustomerAgreementsPanel({ open, agreements, onSelect, onClose }) {
  if (!open) return null;

  const loading = agreements === null;
  const records = agreements ?? [];

  return (
    <div className="rmd-detail-overlay" onClick={onClose}>
      <div className="rmd-detail" onClick={(e) => e.stopPropagation()}>
        <div className="rmd-detail__header">
          <div>
            <span className="rmd-detail__eyebrow">Agreement Module</span>
            <h3>Agreements</h3>
          </div>
          <button type="button" className="rmd-detail__close" onClick={onClose} aria-label="Close details">
            <X size={18} />
          </button>
        </div>

        <div className="rmd-detail__body">
          {loading && (
            <div className="rmd-detail__state">
              <Loader2 size={22} className="rmd-detail__spinner" />
              <span>Loading agreements...</span>
            </div>
          )}

          {!loading && records.length === 0 && (
            <div className="rmd-detail__state">
              <FileX2 size={22} />
              <span>No agreements for this customer yet.</span>
            </div>
          )}

          {!loading && records.length > 0 && (
            <section className="rmd-detail__section">
              <h4>Agreements ({records.length})</h4>
              <div className="customer-records-list">
                {records.map((a) => (
                  <button
                    key={a.id}
                    type="button"
                    className="customer-records-list__item customer-records-list__item--clickable"
                    onClick={() => onSelect(a)}
                  >
                    <div className="customer-records-list__info">
                      <span className="customer-records-list__name">
                        {a.agreement_id} -- {a.agreement_title}
                      </span>
                      <span className="customer-records-list__date">Effective {formatDateMDY(a.effective_date)}</span>
                    </div>
                    <Badge tone={agreementStatusTone(a.status)}>{STATUS_LABELS[a.status] ?? a.status_label}</Badge>
                    <ChevronRight size={15} />
                  </button>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
