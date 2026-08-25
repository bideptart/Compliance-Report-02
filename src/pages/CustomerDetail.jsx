import { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Loader2,
  ServerCrash,
  FileText,
  ClipboardList,
  ShieldCheck,
  FileSignature,
  FileCheck2,
  UploadCloud,
  Save,
} from "lucide-react";
import PageHeader from "../components/PageHeader";
import Section from "../components/Section";
import EmptyState from "../components/EmptyState";
import Badge from "../components/Badge";
import { operationalStatusInfo } from "../utils/rmdStatus";
import CustomerVerificationPanel from "../components/CustomerVerificationPanel";
import RmdDetailPanel from "../components/RmdDetailPanel";
import FccDetailPanel from "../components/FccDetailPanel";
import CustomerRecordsPanel from "../components/CustomerRecordsPanel";
import CustomerAgreementsPanel from "../components/CustomerAgreementsPanel";
import AgreementFormPanel from "../components/AgreementFormPanel";
import AgreementDetailPanel from "../components/AgreementDetailPanel";
import { fetchCustomerDetail, linkCustomerRecords } from "../api/customers";
import { getCustomersListUrl } from "../utils/customersListUrl";
import { fetchRmdDetail } from "../api/rmd";
import { fetchFcc499Detail } from "../api/fcc499";
import { fetchDocuments, uploadDocuments } from "../api/documents";
import { fetchKycDocuments, uploadKycDocument } from "../api/kyc";
import { fetchAgreements, fetchAgreementDetail } from "../api/agreements";
import "../styles/page.css";
import "./Customers.css";
import "../components/RmdResultsTable.css";
import "../components/Toolbar.css";
import "./CustomerDetail.css";

// Every condition the Customers list's Compliance Status dropdown can filter
// by, shown here as a full pass/fail summary for this one customer -- not
// just whichever single filter happened to be selected when they got here.
const COMPLIANCE_CONDITIONS = [
  { key: "fully_compliant", label: "Fully Compliant", passLabel: "Compliant", failLabel: "Not Compliant" },
  { key: "rmd_not_satisfied", label: "RMD Satisfied", invert: true, passLabel: "Satisfied", failLabel: "Not Satisfied" },
  { key: "no_filer_id", label: "Filer ID", invert: true, passLabel: "On File", failLabel: "Missing" },
  { key: "not_active", label: "Operational Status", useOperationalStatus: true },
  { key: "foreign_voice_provider", label: "Foreign Voice Provider", passLabel: "Yes", failLabel: "No", neutral: true },
  // KYC and FSF have no real backend/data source yet -- see ADDITIONAL_MODULES
  // below. Listed here too so this is a genuinely complete status summary,
  // but always "Not Available" rather than a fabricated pass/fail.
  { key: "kyc_status", label: "KYC Status", staticNotAvailable: true },
  { key: "fsf_status", label: "FSF Status", staticNotAvailable: true },
];

// Documents, Tech Form, KYC Document, and Agreement all have a real backend
// -- Tech Form reuses the same Documents upload/storage as Documents itself,
// just tagged with document_type="tech_form" so the two lists never mix
// (see api/documents.js). `recordsKind` points at which per-customer record
// list to show in the popup sidebar (Documents/Tech Form/KYC use
// CustomerRecordsPanel, Agreement uses CustomerAgreementsPanel), and each
// card also gets an inline upload/create control so everything can be done
// from here without leaving the customer's page. FSF Form has no
// backend/model at all, so it stays honestly "Not Available" with View
// disabled.
const UPLOAD_MODULES = [
  { key: "documents", label: "Documents", icon: FileText, recordsKind: "documents" },
  { key: "tech_form", label: "Tech Form", icon: ClipboardList, recordsKind: "tech_form" },
  { key: "kyc_document", label: "KYC Document", icon: ShieldCheck, recordsKind: "kyc" },
  { key: "agreement", label: "Agreement", icon: FileSignature, recordsKind: "agreement" },
  { key: "fsf_form", label: "FSF Form", icon: FileCheck2 },
];

const RECORDS_PANEL_META = {
  documents: { eyebrow: "Documents Module", title: "Uploaded Documents", emptyMessage: "No documents uploaded for this customer yet." },
  tech_form: { eyebrow: "Tech Form", title: "Uploaded Tech Forms", emptyMessage: "No tech forms uploaded for this customer yet." },
  kyc: { eyebrow: "KYC Verification Module", title: "Uploaded KYC Documents", emptyMessage: "No KYC documents uploaded for this customer yet." },
};

export default function CustomerDetail() {
  const { id } = useParams();

  const [customer, setCustomer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Which real RMD/FCC record the person has picked as this customer's real
  // match, when the name-based match was ambiguous (see the dropdown in
  // CustomerVerificationPanel). Passed back to the backend so company name,
  // country, operational status, filer ID, and compliance are all
  // recomputed from that specific record as a preview -- see
  // api/customers.js fetchCustomerDetail and
  // verification.customer.get_customer_verification. Stays null (and the
  // real saved link, customer.linked_rmd_record_id, takes over) once
  // nothing is being actively re-picked this session.
  const [selectedRmdRecordId, setSelectedRmdRecordId] = useState(null);
  const [selectedFccRecordId, setSelectedFccRecordId] = useState(null);

  // The full candidate list from the moment each side was first found
  // ambiguous -- captured once so the dropdown can keep showing every
  // option even after picking one narrows the live verification response
  // down to a single record (see CustomerVerificationPanel).
  const [rmdCandidates, setRmdCandidates] = useState([]);
  const [fccCandidates, setFccCandidates] = useState([]);

  const [savingLink, setSavingLink] = useState(false);
  const [saveLinkError, setSaveLinkError] = useState(null);

  const [rmdSelectedId, setRmdSelectedId] = useState(null);
  const [rmdDetail, setRmdDetail] = useState(null);
  const [rmdDetailLoading, setRmdDetailLoading] = useState(false);
  const [rmdDetailError, setRmdDetailError] = useState(null);

  const [fccSelectedId, setFccSelectedId] = useState(null);
  const [fccDetail, setFccDetail] = useState(null);
  const [fccDetailLoading, setFccDetailLoading] = useState(false);
  const [fccDetailError, setFccDetailError] = useState(null);

  // Real per-customer record counts for the Compliance Documents cards --
  // null while unknown, [] once loaded and genuinely empty.
  const [documentsRecords, setDocumentsRecords] = useState(null);
  const [techFormRecords, setTechFormRecords] = useState(null);
  const [kycRecords, setKycRecords] = useState(null);
  const [recordsPanelKind, setRecordsPanelKind] = useState(null);

  const [documentsUploading, setDocumentsUploading] = useState(false);
  const [documentsUploadError, setDocumentsUploadError] = useState(null);
  const [techFormUploading, setTechFormUploading] = useState(false);
  const [techFormUploadError, setTechFormUploadError] = useState(null);
  const [kycUploading, setKycUploading] = useState(false);
  const [kycUploadError, setKycUploadError] = useState(null);
  const documentsFileInputRef = useRef(null);
  const techFormFileInputRef = useRef(null);
  const kycFileInputRef = useRef(null);

  // This customer's own agreements -- created from this page (see
  // AgreementFormPanel below) and viewed via CustomerAgreementsPanel /
  // AgreementDetailPanel, the same "list, then one record" flow
  // Documents/Tech Form/KYC use.
  const [agreements, setAgreements] = useState(null);
  const [agreementsError, setAgreementsError] = useState(null);
  const [agreementsListOpen, setAgreementsListOpen] = useState(false);

  const [agreementFormOpen, setAgreementFormOpen] = useState(false);

  const [agreementDetailOpen, setAgreementDetailOpen] = useState(false);
  const [agreementDetailLoading, setAgreementDetailLoading] = useState(false);
  const [agreementDetailError, setAgreementDetailError] = useState(null);
  const [agreementDetail, setAgreementDetail] = useState(null);

  const loadDocuments = () => {
    fetchDocuments({ customerId: id, documentType: "document" })
      .then((data) => setDocumentsRecords(data.results ?? []))
      .catch(() => setDocumentsRecords([]));
  };

  const loadTechForm = () => {
    fetchDocuments({ customerId: id, documentType: "tech_form" })
      .then((data) => setTechFormRecords(data.results ?? []))
      .catch(() => setTechFormRecords([]));
  };

  const loadKyc = () => {
    fetchKycDocuments({ customerId: id })
      .then((data) => setKycRecords(data.results ?? []))
      .catch(() => setKycRecords([]));
  };

  const loadAgreements = () => {
    fetchAgreements({ customerId: id, page: 1 })
      .then((data) => {
        setAgreements(data.results ?? []);
        setAgreementsError(null);
      })
      .catch(() => {
        setAgreements([]);
        setAgreementsError("Unable to load agreements for this customer.");
      });
  };

  useEffect(() => {
    setDocumentsRecords(null);
    setTechFormRecords(null);
    setKycRecords(null);
    setAgreements(null);
    // A fresh customer's own ambiguity has nothing to do with whatever was
    // picked for the last one -- never carry a selection across customers.
    setSelectedRmdRecordId(null);
    setSelectedFccRecordId(null);
    setRmdCandidates([]);
    setFccCandidates([]);
    setSaveLinkError(null);

    loadDocuments();
    loadTechForm();
    loadKyc();
    loadAgreements();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchCustomerDetail(id, { rmdRecordId: selectedRmdRecordId, fccRecordId: selectedFccRecordId })
      .then((data) => {
        if (cancelled) return;
        setCustomer(data);
        // Captured once, the first time this side is genuinely ambiguous
        // and not yet saved -- never overwritten by a later preview
        // response, which only carries the single record being previewed
        // (see CustomerVerificationPanel's candidatesOverride).
        if (data.rmd_verification?.status === "multiple_matches" && !data.linked_rmd_record_id) {
          setRmdCandidates((prev) => (prev.length > 0 ? prev : data.rmd_verification.matched_records ?? []));
        }
        if (data.fcc_verification?.status === "multiple_matches" && !data.linked_fcc_record_id) {
          setFccCandidates((prev) => (prev.length > 0 ? prev : data.fcc_verification.matched_records ?? []));
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setCustomer(null);
        setError(
          err.status === 0
            ? "Cannot connect to the compliance server. Please make sure the backend is running."
            : "Unable to load this customer's verification record."
        );
      })
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
    };
  }, [id, selectedRmdRecordId, selectedFccRecordId]);

  // Picking a candidate from the dropdown only previews it -- it recomputes
  // the Verification Summary/Compliance Status above from that record, but
  // deliberately does NOT open the record's own detail side panel. Opening
  // that panel is a separate, explicit action (see handleOpenRmdRecord
  // below), triggered only by clicking the tile itself.
  const handleSelectRmdRecord = (recordId) => setSelectedRmdRecordId(recordId);
  const handleSelectFccRecord = (recordId) => setSelectedFccRecordId(recordId);

  const handleOpenRmdRecord = (recordId) => {
    setRmdSelectedId(recordId);
    setRmdDetail(null);
    setRmdDetailError(null);
    setRmdDetailLoading(true);

    fetchRmdDetail(recordId)
      .then((data) => setRmdDetail(data))
      .catch(() => setRmdDetailError("Unable to load this RMD record's details."))
      .finally(() => setRmdDetailLoading(false));
  };

  const handleOpenFccRecord = (recordId) => {
    setFccSelectedId(recordId);
    setFccDetail(null);
    setFccDetailError(null);
    setFccDetailLoading(true);

    fetchFcc499Detail(recordId)
      .then((data) => setFccDetail(data))
      .catch(() => setFccDetailError("Unable to load this FCC record's details."))
      .finally(() => setFccDetailLoading(false));
  };

  // Persists whichever side(s) actually have a pending pick this session --
  // never sends a side that was never touched, so an already-saved link on
  // the other side (from a previous visit) is never accidentally cleared.
  // See api/customers.js linkCustomerRecords + CustomerLinkRecordsView.
  const handleSaveLinkedRecords = () => {
    const payload = {};
    if (selectedRmdRecordId != null) payload.rmdRecordId = selectedRmdRecordId;
    if (selectedFccRecordId != null) payload.fccRecordId = selectedFccRecordId;
    if (Object.keys(payload).length === 0) return;

    setSaveLinkError(null);
    setSavingLink(true);
    linkCustomerRecords(id, payload)
      .then((data) => {
        setCustomer(data);
        setSelectedRmdRecordId(null);
        setSelectedFccRecordId(null);
        setRmdCandidates([]);
        setFccCandidates([]);
      })
      .catch(() => setSaveLinkError("Unable to save the selected record. Please try again."))
      .finally(() => setSavingLink(false));
  };

  const handleDocumentsFileChange = (e) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length === 0) return;

    setDocumentsUploadError(null);
    setDocumentsUploading(true);
    uploadDocuments({ customerId: id, files, documentType: "document" })
      .then(() => loadDocuments())
      .catch((err) => setDocumentsUploadError(err.message || "Upload failed. Please try again."))
      .finally(() => {
        setDocumentsUploading(false);
        if (documentsFileInputRef.current) documentsFileInputRef.current.value = "";
      });
  };

  const handleTechFormFileChange = (e) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length === 0) return;

    setTechFormUploadError(null);
    setTechFormUploading(true);
    uploadDocuments({ customerId: id, files, documentType: "tech_form" })
      .then(() => loadTechForm())
      .catch((err) => setTechFormUploadError(err.message || "Upload failed. Please try again."))
      .finally(() => {
        setTechFormUploading(false);
        if (techFormFileInputRef.current) techFormFileInputRef.current.value = "";
      });
  };

  const handleKycFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setKycUploadError(null);
    setKycUploading(true);
    uploadKycDocument({ customerId: id, file })
      .then(() => loadKyc())
      .catch((err) => setKycUploadError(err.message || "Upload failed. Please try again."))
      .finally(() => {
        setKycUploading(false);
        if (kycFileInputRef.current) kycFileInputRef.current.value = "";
      });
  };

  const openCreateAgreement = () => {
    setAgreementFormOpen(true);
  };

  const openViewAgreement = (agreement) => {
    setAgreementsListOpen(false);
    setAgreementDetailOpen(true);
    setAgreementDetailLoading(true);
    setAgreementDetailError(null);
    setAgreementDetail(null);

    fetchAgreementDetail(agreement.id)
      .then((data) => setAgreementDetail(data))
      .catch(() => setAgreementDetailError("Unable to load this agreement's details."))
      .finally(() => setAgreementDetailLoading(false));
  };

  const handleAgreementSaved = () => {
    setAgreementFormOpen(false);
    loadAgreements();
  };

  const isAmbiguousMatch =
    customer?.rmd_verification?.status === "multiple_matches" || customer?.fcc_verification?.status === "multiple_matches";

  const hasPendingSelection = selectedRmdRecordId != null || selectedFccRecordId != null;

  return (
    <div>
      <Link to={getCustomersListUrl()} className="customer-detail__back">
        <ArrowLeft size={15} />
        Back to Customers
      </Link>

      <PageHeader title={customer?.carrier ?? customer?.company_name ?? "Customer"} />

      {loading && (
        <div className="customers-loading">
          <Loader2 size={22} className="customers-loading__spinner" />
          <span>Loading customer verification record...</span>
        </div>
      )}

      {!loading && error && (
        <EmptyState icon={ServerCrash} title="Unable to load customer" description={error} />
      )}

      {!loading && !error && customer && (
        <>
          <div style={{ height: 18 }} />

          <Section
            title="Verification Summary"
            description="RMD, FCC, and FRN match status"
            actions={
              hasPendingSelection && (
                <button
                  type="button"
                  className="dashboard-section-link"
                  onClick={handleSaveLinkedRecords}
                  disabled={savingLink}
                >
                  {savingLink ? "Saving..." : "Save Selection"} <Save size={13} />
                </button>
              )
            }
          >
            <CustomerVerificationPanel
              customer={customer}
              onSelectRmdRecord={handleSelectRmdRecord}
              onSelectFccRecord={handleSelectFccRecord}
              onOpenRmdRecord={handleOpenRmdRecord}
              onOpenFccRecord={handleOpenFccRecord}
              selectedRmdRecordId={selectedRmdRecordId}
              selectedFccRecordId={selectedFccRecordId}
              rmdCandidatesOverride={rmdCandidates.length > 0 ? rmdCandidates : null}
              fccCandidatesOverride={fccCandidates.length > 0 ? fccCandidates : null}
            />
            {saveLinkError && <p className="rmd-detail__download-error">{saveLinkError}</p>}
          </Section>

          <div style={{ height: 18 }} />

          <div className="customer-detail__two-col">
            <Section
              title="Compliance Status"
              description={
                isAmbiguousMatch
                  ? "Select the real RMD/FCC record above to compute this customer's compliance."
                  : undefined
              }
            >
              <div className="compliance-grid">
                {COMPLIANCE_CONDITIONS.map(
                  ({ key, label, invert, passLabel, failLabel, neutral, useOperationalStatus, staticNotAvailable }) => {
                    // A carrier name that matches more than one real RMD or
                    // FCC record is genuinely unresolved -- company name,
                    // country, and FRN could all still change once a
                    // specific record is picked (see the dropdowns in
                    // CustomerVerificationPanel), so every condition here
                    // stays an honest "Not Available" rather than computing
                    // a pass/fail against data that might not even be the
                    // right company yet.
                    if (staticNotAvailable || isAmbiguousMatch) {
                      return (
                        <div key={key} className="compliance-grid__item">
                          <span className="compliance-grid__label">{label}</span>
                          <Badge tone="neutral">Not Available</Badge>
                        </div>
                      );
                    }

                    if (useOperationalStatus) {
                      // Real Active/Inactive/Not Available, not the
                      // "not_active" filter flag inverted -- that flag is
                      // only meaningful relative to an FCC match, and reads
                      // misleadingly as "Active" with no FCC match at all.
                      const status = operationalStatusInfo(customer.operational_status);
                      const tone = customer.operational_status ? status.tone : "neutral";
                      const text = customer.operational_status ? status.label : "Not Available";
                      return (
                        <div key={key} className="compliance-grid__item">
                          <span className="compliance-grid__label">{label}</span>
                          <Badge tone={tone}>{text}</Badge>
                        </div>
                      );
                    }

                    const raw = Boolean(customer.compliance?.[key]);
                    const passed = invert ? !raw : raw;
                    // Foreign Voice Provider is informational, not
                    // pass/fail -- teal when true, plain neutral gray when
                    // false, never the amber "warning" tone (it isn't a
                    // problem).
                    const tone = neutral ? (raw ? "teal" : "neutral") : passed ? "success" : "danger";
                    const text = passed ? passLabel : failLabel;
                    return (
                      <div key={key} className="compliance-grid__item">
                        <span className="compliance-grid__label">{label}</span>
                        <Badge tone={tone}>{text}</Badge>
                      </div>
                    );
                  }
                )}
              </div>
            </Section>

            <Section title="Compliance Documents">
              <div className="module-status-grid">
                {UPLOAD_MODULES.map(({ key, label, icon: Icon, recordsKind }) => {
                  if (recordsKind === "agreement") {
                    const count = agreements?.length ?? 0;
                    const badgeTone = agreements === null ? "neutral" : count > 0 ? "success" : "neutral";
                    const badgeText = agreements === null ? "Loading..." : count > 0 ? `${count} Agreement${count === 1 ? "" : "s"}` : "Not Available";
                    return (
                      <div key={key} className="module-status-card">
                        <span className="module-status-card__icon">
                          <Icon size={16} strokeWidth={2} />
                        </span>
                        <span className="module-status-card__label">{label}</span>
                        <div className="module-status-card__actions">
                          <Badge tone={badgeTone}>{badgeText}</Badge>
                          <button
                            type="button"
                            className="module-status-card__view-btn"
                            disabled={agreements === null}
                            onClick={() => setAgreementsListOpen(true)}
                          >
                            View
                          </button>
                          <button type="button" className="module-status-card__view-btn" onClick={openCreateAgreement}>
                            <UploadCloud size={13} />
                            Upload
                          </button>
                        </div>
                      </div>
                    );
                  }

                  const records =
                    recordsKind === "documents" ? documentsRecords : recordsKind === "tech_form" ? techFormRecords : recordsKind === "kyc" ? kycRecords : null;
                  const uploading =
                    recordsKind === "documents" ? documentsUploading : recordsKind === "tech_form" ? techFormUploading : recordsKind === "kyc" ? kycUploading : false;
                  const uploadError =
                    recordsKind === "documents" ? documentsUploadError : recordsKind === "tech_form" ? techFormUploadError : recordsKind === "kyc" ? kycUploadError : null;
                  const fileInputRef =
                    recordsKind === "documents" ? documentsFileInputRef : recordsKind === "tech_form" ? techFormFileInputRef : recordsKind === "kyc" ? kycFileInputRef : null;
                  const handleFileChange =
                    recordsKind === "documents" ? handleDocumentsFileChange : recordsKind === "tech_form" ? handleTechFormFileChange : recordsKind === "kyc" ? handleKycFileChange : null;

                  if (recordsKind) {
                    const count = records?.length ?? 0;
                    const badgeTone = records === null ? "neutral" : count > 0 ? "success" : "neutral";
                    const badgeText = records === null ? "Loading..." : count > 0 ? `${count} File${count === 1 ? "" : "s"}` : "Not Available";
                    const multiple = recordsKind === "documents" || recordsKind === "tech_form";
                    return (
                      <div key={key} className="module-status-card">
                        <span className="module-status-card__icon">
                          <Icon size={16} strokeWidth={2} />
                        </span>
                        <span className="module-status-card__label">{label}</span>
                        <div className="module-status-card__actions">
                          <Badge tone={badgeTone}>{badgeText}</Badge>
                          <button
                            type="button"
                            className="module-status-card__view-btn"
                            disabled={records === null}
                            onClick={() => setRecordsPanelKind(recordsKind)}
                          >
                            View
                          </button>
                          <input
                            ref={fileInputRef}
                            type="file"
                            className="module-status-card__file-input"
                            multiple={multiple}
                            accept={multiple ? ".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,.csv,.txt" : ".pdf,.png,.jpg,.jpeg"}
                            onChange={handleFileChange}
                          />
                          <button
                            type="button"
                            className="module-status-card__view-btn"
                            disabled={uploading}
                            onClick={() => fileInputRef.current?.click()}
                          >
                            {uploading ? <Loader2 size={13} className="module-status-card__spinner" /> : <UploadCloud size={13} />}
                            {uploading ? "Uploading..." : "Upload"}
                          </button>
                        </div>
                        {uploadError && <p className="module-status-card__error">{uploadError}</p>}
                      </div>
                    );
                  }

                  return (
                    <div key={key} className="module-status-card">
                      <span className="module-status-card__icon">
                        <Icon size={16} strokeWidth={2} />
                      </span>
                      <span className="module-status-card__label">{label}</span>
                      <div className="module-status-card__actions">
                        <Badge tone="neutral">Not Available</Badge>
                        <button
                          type="button"
                          className="module-status-card__view-btn"
                          disabled
                          title="No module or document exists for this yet"
                        >
                          View
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Section>
          </div>
        </>
      )}

      <RmdDetailPanel
        open={rmdSelectedId !== null}
        loading={rmdDetailLoading}
        error={rmdDetailError}
        record={rmdDetail}
        onClose={() => setRmdSelectedId(null)}
      />

      <FccDetailPanel
        open={fccSelectedId !== null}
        loading={fccDetailLoading}
        error={fccDetailError}
        record={fccDetail}
        onClose={() => setFccSelectedId(null)}
      />

      <CustomerRecordsPanel
        open={recordsPanelKind !== null}
        loading={false}
        error={null}
        eyebrow={recordsPanelKind ? RECORDS_PANEL_META[recordsPanelKind].eyebrow : ""}
        title={recordsPanelKind ? RECORDS_PANEL_META[recordsPanelKind].title : ""}
        emptyMessage={recordsPanelKind ? RECORDS_PANEL_META[recordsPanelKind].emptyMessage : ""}
        records={
          (recordsPanelKind === "documents"
            ? documentsRecords
            : recordsPanelKind === "tech_form"
            ? techFormRecords
            : kycRecords) ?? []
        }
        onClose={() => setRecordsPanelKind(null)}
      />

      {customer && (
        <AgreementFormPanel
          open={agreementFormOpen}
          mode="create"
          agreement={null}
          customers={[customer]}
          lockedCustomer={customer}
          onClose={() => setAgreementFormOpen(false)}
          onSaved={handleAgreementSaved}
        />
      )}

      <CustomerAgreementsPanel
        open={agreementsListOpen}
        agreements={agreements}
        onSelect={openViewAgreement}
        onClose={() => setAgreementsListOpen(false)}
      />

      <AgreementDetailPanel
        open={agreementDetailOpen}
        loading={agreementDetailLoading}
        error={agreementDetailError}
        agreement={agreementDetail}
        onClose={() => setAgreementDetailOpen(false)}
      />
    </div>
  );
}
