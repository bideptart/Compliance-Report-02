import { X, ExternalLink, Loader2, AlertTriangle, FileX2 } from "lucide-react";
import "./RmdDetailPanel.css";
import "./CustomerRecordsPanel.css";

function formatTimestamp(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

// Same sliding side panel as RmdDetailPanel/FccDetailPanel (reuses their
// CSS classes), showing the real files a specific customer has uploaded --
// through the KYC or Documents module -- rather than the module's own
// full library.
export default function CustomerRecordsPanel({ open, loading, error, eyebrow, title, records, emptyMessage, onClose }) {
  if (!open) return null;

  return (
    <div className="rmd-detail-overlay" onClick={onClose}>
      <div className="rmd-detail" onClick={(e) => e.stopPropagation()}>
        <div className="rmd-detail__header">
          <div>
            <span className="rmd-detail__eyebrow">{eyebrow}</span>
            <h3>{title}</h3>
          </div>
          <button type="button" className="rmd-detail__close" onClick={onClose} aria-label="Close details">
            <X size={18} />
          </button>
        </div>

        <div className="rmd-detail__body">
          {loading && (
            <div className="rmd-detail__state">
              <Loader2 size={22} className="rmd-detail__spinner" />
              <span>Loading records...</span>
            </div>
          )}

          {!loading && error && (
            <div className="rmd-detail__state rmd-detail__state--error">
              <AlertTriangle size={22} />
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && records.length === 0 && (
            <div className="rmd-detail__state">
              <FileX2 size={22} />
              <span>{emptyMessage}</span>
            </div>
          )}

          {!loading && !error && records.length > 0 && (
            <section className="rmd-detail__section">
              <h4>Uploaded Files ({records.length})</h4>
              <div className="customer-records-list">
                {records.map((record) => (
                  <div key={record.id} className="customer-records-list__item">
                    <div className="customer-records-list__info">
                      <span className="customer-records-list__name">{record.file_name}</span>
                      <span className="customer-records-list__date">
                        Uploaded {formatTimestamp(record.uploaded_at)}
                      </span>
                    </div>
                    {record.file_url && (
                      <a
                        className="customer-records-list__view"
                        href={record.file_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        View
                        <ExternalLink size={13} />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
