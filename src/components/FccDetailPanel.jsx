import { X, ExternalLink, Loader2, AlertTriangle } from "lucide-react";
import FrnVerificationSection from "./FrnVerificationSection";
import "./RmdDetailPanel.css";

function Field({ label, value }) {
  return (
    <div className="rmd-detail__field">
      <span className="rmd-detail__field-label">{label}</span>
      <span className="rmd-detail__field-value">{value ?? "—"}</span>
    </div>
  );
}

export default function FccDetailPanel({ open, loading, error, record, onClose }) {
  if (!open) return null;

  return (
    <div className="rmd-detail-overlay" onClick={onClose}>
      <div className="rmd-detail" onClick={(e) => e.stopPropagation()}>
        <div className="rmd-detail__header">
          <div>
            <span className="rmd-detail__eyebrow">FCC Form 499 Record</span>
            <h3>{record?.legal_name ?? "Filing details"}</h3>
          </div>
          <button type="button" className="rmd-detail__close" onClick={onClose} aria-label="Close details">
            <X size={18} />
          </button>
        </div>

        <div className="rmd-detail__body">
          {loading && (
            <div className="rmd-detail__state">
              <Loader2 size={22} className="rmd-detail__spinner" />
              <span>Loading record details...</span>
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
              <section className="rmd-detail__section">
                <h4>Filer Information</h4>
                <div className="rmd-detail__grid">
                  <Field label="Filer ID" value={record.filer_id} />
                  <Field label="Legal Name" value={record.legal_name} />
                  <Field label="CORES ID / FRN" value={record.cores_id} />
                  <Field label="Registration Current As Of" value={record.registration_current_as_of} />
                </div>
              </section>

              <section className="rmd-detail__section">
                <h4>Headquarters & Contact</h4>
                <div className="rmd-detail__grid">
                  <Field label="Address" value={record.headquarters_address} />
                  <Field label="City" value={record.headquarters_city} />
                  <Field label="State" value={record.headquarters_state} />
                  <Field label="ZIP" value={record.headquarters_zip} />
                  <Field label="Customer Phone" value={record.customer_phone} />
                  <Field label="FCC Registration Information" value={record.fcc_registration_information} />
                </div>
              </section>

              <FrnVerificationSection verification={record.frn_verification} />

              {record.detail_url && (
                <a
                  className="rmd-detail__official-link"
                  href={record.detail_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  View Official FCC Record
                  <ExternalLink size={15} />
                </a>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
