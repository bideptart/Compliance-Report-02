import { useState } from "react";
import { X, ExternalLink, Loader2, AlertTriangle, Download } from "lucide-react";
import Badge from "./Badge";
import { agreementStatusTone, formatDateMDY, formatDateTimeMDY } from "../utils/agreementStatus";
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
  draft: "Draft",
  pending_review: "Pending Review",
  active: "Active",
  expiring_soon: "Expiring Soon",
  expired: "Expired",
  terminated: "Terminated",
};

const TYPE_LABELS = {
  customer_agreement: "Customer Agreement",
  carrier_agreement: "Carrier Agreement",
  service_agreement: "Service Agreement",
  compliance_agreement: "Compliance Agreement",
  other: "Other",
};

export default function AgreementDetailPanel({ open, loading, error, agreement, onClose }) {
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState(null);

  if (!open) return null;

  // A plain <a download> only forces a save for same-origin files -- this
  // document is served by the Django backend on a different origin
  // (localhost:8000 vs the frontend's 5173), so browsers silently ignore
  // the attribute there and just navigate to it like "View Document"
  // does. Fetching the bytes and saving them as a blob works regardless of
  // origin, so "Download" always actually downloads instead of opening a
  // new tab.
  const handleDownload = async () => {
    setDownloadError(null);
    setDownloading(true);
    try {
      const response = await fetch(agreement.document_url);
      if (!response.ok) throw new Error();
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = agreement.document_name || "document";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(blobUrl);
    } catch {
      setDownloadError("Unable to download this file. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="rmd-detail-overlay" onClick={onClose}>
      <div className="rmd-detail" onClick={(e) => e.stopPropagation()}>
        <div className="rmd-detail__header">
          <div>
            <span className="rmd-detail__eyebrow">Agreement</span>
            <h3>{agreement?.agreement_title ?? "Agreement details"}</h3>
          </div>
          <button type="button" className="rmd-detail__close" onClick={onClose} aria-label="Close details">
            <X size={18} />
          </button>
        </div>

        <div className="rmd-detail__body">
          {loading && (
            <div className="rmd-detail__state">
              <Loader2 size={22} className="rmd-detail__spinner" />
              <span>Loading agreement details...</span>
            </div>
          )}

          {!loading && error && (
            <div className="rmd-detail__state rmd-detail__state--error">
              <AlertTriangle size={22} />
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && agreement && (
            <>
              <div className="rmd-detail__status-row">
                <Badge tone={agreementStatusTone(agreement.status)}>{STATUS_LABELS[agreement.status] ?? agreement.status}</Badge>
              </div>

              <section className="rmd-detail__section">
                <h4>Agreement Information</h4>
                <div className="rmd-detail__grid">
                  <Field label="Agreement ID" value={agreement.agreement_id} />
                  <Field label="Agreement Title" value={agreement.agreement_title} />
                  <Field label="Agreement Type" value={TYPE_LABELS[agreement.agreement_type] ?? agreement.agreement_type} />
                  <Field label="Auto Renewal" value={agreement.auto_renewal ? "Yes" : "No"} />
                  <Field label="Effective Date" value={formatDateMDY(agreement.effective_date)} />
                  <Field label="Expiry Date" value={formatDateMDY(agreement.expiry_date)} />
                  {agreement.previous_agreement_id && (
                    <Field label="Renewed From" value={agreement.previous_agreement_id} />
                  )}
                  {agreement.termination_reason && (
                    <Field label="Termination Reason" value={agreement.termination_reason} />
                  )}
                </div>
                {agreement.notes && <Field label="Notes" value={agreement.notes} />}
              </section>

              <section className="rmd-detail__section">
                <h4>Customer Information</h4>
                <div className="rmd-detail__grid">
                  <Field label="Company Name" value={agreement.customer_info?.company_name ?? agreement.customer_name} />
                  <Field label="Country of Origin" value={agreement.customer_info?.country} />
                  <Field label="FRN" value={agreement.customer_info?.frn} />
                </div>
              </section>

              <section className="rmd-detail__section">
                <h4>Document</h4>
                {agreement.document_url ? (
                  <>
                    <Field label="File Name" value={agreement.document_name} />
                    <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
                      <a
                        className="rmd-detail__official-link"
                        href={agreement.document_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        View Document
                        <ExternalLink size={15} />
                      </a>
                      <button
                        type="button"
                        className="rmd-detail__official-link rmd-detail__official-link--button"
                        onClick={handleDownload}
                        disabled={downloading}
                      >
                        {downloading ? "Downloading..." : "Download"}
                        {downloading ? <Loader2 size={15} className="rmd-detail__spinner" /> : <Download size={15} />}
                      </button>
                    </div>
                    {downloadError && <p className="rmd-detail__download-error">{downloadError}</p>}
                  </>
                ) : (
                  <span className="rmd-detail__field-value">No document uploaded.</span>
                )}
              </section>

              <section className="rmd-detail__section">
                <h4>Activity</h4>
                <div className="rmd-detail__grid">
                  <Field label="Created Date" value={formatDateTimeMDY(agreement.created_at)} />
                  <Field label="Last Updated Date" value={formatDateTimeMDY(agreement.updated_at)} />
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
