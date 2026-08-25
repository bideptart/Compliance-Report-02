import { useState } from "react";
import { X, ExternalLink, Loader2, AlertTriangle, Download } from "lucide-react";
import StatusBadge from "./StatusBadge";
import FrnVerificationSection from "./FrnVerificationSection";
import { rmdDownloadUrl } from "../api/rmd";
import "./RmdDetailPanel.css";

function Field({ label, value }) {
  return (
    <div className="rmd-detail__field">
      <span className="rmd-detail__field-label">{label}</span>
      <span className="rmd-detail__field-value">{value ?? "—"}</span>
    </div>
  );
}

export default function RmdDetailPanel({ open, loading, error, record, onClose }) {
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState(null);

  if (!open) return null;

  // The record's own filing_url is a JavaScript-rendered FCC ServiceNow
  // page -- a plain <a download> (or a same-tab navigation) can't capture
  // its content, so this fetches the real official filing PDF the backend
  // proxies from the FCC's own RMD portal (see rmd/official_pdf.py) as a
  // blob and saves it, the same pattern AgreementDetailPanel uses for its
  // document. Saved under the company's own name (not the FCC's own
  // attachment filename) so it's recognizable in the user's downloads.
  const handleDownload = async () => {
    setDownloadError(null);
    setDownloading(true);
    try {
      const response = await fetch(rmdDownloadUrl(record.id));
      if (!response.ok) throw new Error();
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      const companyName = (record.business_name || `RMD-${record.number || record.id}`)
        .replace(/[\\/:*?"<>|]+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
      link.download = `${companyName}-RMD.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(blobUrl);
    } catch {
      setDownloadError("Unable to download this record. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="rmd-detail-overlay" onClick={onClose}>
      <div className="rmd-detail" onClick={(e) => e.stopPropagation()}>
        <div className="rmd-detail__header">
          <div>
            <span className="rmd-detail__eyebrow">RMD Record</span>
            <h3>{record?.business_name ?? "Filing details"}</h3>
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
              <div className="rmd-detail__status-row">
                <StatusBadge label={record.implementation} />
              </div>

              <section className="rmd-detail__section">
                <h4>Business Information</h4>
                <div className="rmd-detail__grid">
                  <Field label="RMD Number" value={record.number} />
                  <Field label="FRN" value={record.frn} />
                  <Field label="Business Name" value={record.business_name} />
                  <Field label="Country" value={record.country} />
                  <Field label="Foreign Voice Provider" value={record.foreign_voice_provider} />
                  <Field label="Other FRNs" value={record.other_frns} />
                  <Field label="Other DBA Names" value={record.other_dba_names} />
                  <Field label="Previous DBA Names" value={record.previous_dba_names} />
                </div>
                <Field label="Business Address" value={record.business_address} />
              </section>

              <section className="rmd-detail__section">
                <h4>Robocall Mitigation Contact</h4>
                <div className="rmd-detail__grid">
                  <Field label="Contact Name" value={record.robocall_mitigation_contact_name} />
                  <Field label="Title" value={record.contact_title} />
                  <Field label="Department" value={record.contact_department} />
                  <Field label="Country" value={record.contact_country} />
                  <Field label="Phone" value={record.contact_telephone_number} />
                  <Field label="Extension" value={record.contact_phone_extension} />
                </div>
                <Field label="Contact Business Address" value={record.contact_business_address} />
              </section>

              <section className="rmd-detail__section">
                <h4>Provider Role & Filing</h4>
                <div className="rmd-detail__grid">
                  <Field label="Voice Service Provider" value={record.voice_service_provider_choice} />
                  <Field label="Gateway Provider" value={record.gateway_provider_choice} />
                  <Field label="Intermediate Provider" value={record.intermediate_provider_choice} />
                  <Field label="Last Updated" value={record.last_updated} />
                  <Field label="Last Recertified" value={record.last_recertified} />
                </div>
              </section>

              <FrnVerificationSection verification={record.frn_verification} />

              <div className="rmd-detail__actions">
                {record.filing_url && (
                  <a
                    className="rmd-detail__action-btn"
                    href={record.filing_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    View on Official FCC Site
                    <ExternalLink size={15} />
                  </a>
                )}
                <button
                  type="button"
                  className="rmd-detail__action-btn"
                  onClick={handleDownload}
                  disabled={downloading}
                >
                  {downloading ? "Downloading..." : "Download"}
                  {downloading ? <Loader2 size={15} className="rmd-detail__spinner" /> : <Download size={15} />}
                </button>
              </div>
              {downloadError && <p className="rmd-detail__download-error">{downloadError}</p>}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
