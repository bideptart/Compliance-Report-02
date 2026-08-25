import { ChevronRight, ShieldQuestion } from "lucide-react";
import Badge from "./Badge";
import EmptyState from "./EmptyState";
import {
  customerFrnMatchInfo,
  fccVerificationStatusInfo,
  rmdVerificationStatusInfo,
  shortVerifiedStatusInfo,
} from "../utils/rmdStatus";
import "./CustomerVerificationPanel.css";

function VerificationTile({
  title,
  verification,
  statusInfo,
  onSelectRecord,
  onOpenRecord,
  recordLabelField,
  recordNumberField,
  numberLabel,
  selectedRecordId,
  candidatesOverride,
}) {
  const short = shortVerifiedStatusInfo(verification?.status);
  const full = statusInfo(verification?.status);
  // Once a candidate is picked to preview, the backend re-verifies against
  // just that one record -- verification.matched_records narrows to a
  // single entry, which would silently collapse the dropdown back down to
  // the "click to view" single-match tile. candidatesOverride is the full
  // original candidate list captured the moment this side was first found
  // ambiguous (see CustomerDetail), so the dropdown keeps every option
  // available until the choice is actually saved.
  const matches = candidatesOverride ?? verification?.matched_records ?? [];
  const hasDropdown = matches.length > 1;
  const clickableSingle = !hasDropdown && matches.length === 1 && verification?.record_id;

  // The record whose detail panel opens when the tile rectangle itself is
  // clicked -- the resolved single match, or (in dropdown mode) whichever
  // candidate is currently selected/previewed. Never fires from picking a
  // dropdown option -- that only updates the selection (see onSelectRecord
  // below); the rectangle is a separate, deliberate "view details" action.
  const clickableRecordId = clickableSingle ? verification.record_id : hasDropdown ? selectedRecordId : null;
  const isClickable = Boolean(clickableRecordId);

  // The actual record's own identifying number, shown on the tile once
  // resolved (whether that's a real single match, a live preview, or a
  // saved link) -- verification.matched_records always narrows to exactly
  // the one record the backend just verified against, regardless of
  // candidatesOverride.
  const resolvedRecord = verification?.status === "present" ? verification.matched_records?.[0] : null;
  const displayNumber = resolvedRecord?.[recordNumberField];

  return (
    <div
      className={"customer-verification-tile" + (isClickable ? " customer-verification-tile--clickable" : "")}
      onClick={isClickable ? () => onOpenRecord(clickableRecordId) : undefined}
      role={isClickable ? "button" : undefined}
      tabIndex={isClickable ? 0 : undefined}
    >
      <div className="customer-verification-tile__head">
        <span className="customer-verification-tile__title">{title}</span>
        <Badge tone={short.tone}>{short.label}</Badge>
      </div>

      <span className="customer-verification-tile__full-status">{full.label}</span>

      {displayNumber && (
        <span className="customer-verification-tile__number">
          {numberLabel}: {displayNumber}
        </span>
      )}

      {isClickable && (
        <span className="customer-verification-tile__cta">
          Click to view <ChevronRight size={14} />
        </span>
      )}

      {hasDropdown && (
        <select
          className="customer-verification-tile__select"
          // Stays on whichever candidate was picked (or the saved link,
          // once CustomerDetail seeds it in) instead of resetting back to
          // the placeholder every time -- the dropdown is the visible
          // record of what's currently selected/previewed.
          value={selectedRecordId != null ? String(selectedRecordId) : ""}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => {
            if (e.target.value) onSelectRecord(Number(e.target.value));
          }}
        >
          <option value="" disabled>
            {matches.length} matches — select one
          </option>
          {matches.map((match) => (
            <option key={match.id} value={match.id}>
              {match[recordLabelField] ?? "Unnamed record"}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}

export default function CustomerVerificationPanel({
  customer,
  onSelectRmdRecord,
  onSelectFccRecord,
  onOpenRmdRecord,
  onOpenFccRecord,
  selectedRmdRecordId,
  selectedFccRecordId,
  rmdCandidatesOverride,
  fccCandidatesOverride,
}) {
  if (!customer) {
    return (
      <EmptyState
        icon={ShieldQuestion}
        title="Select a customer above"
        description="Click a carrier in the results table to view its full RMD + FCC verification."
      />
    );
  }

  const frnMatch = customerFrnMatchInfo(customer.frn_verification?.status);
  const rmdFrn = customer.rmd_verification?.frn;
  const fccFrn = customer.fcc_verification?.frn;

  return (
    <div className="customer-verification">
      <div className="customer-verification__summary">
        <div className="customer-verification__field">
          <span className="customer-verification__field-label">Carrier</span>
          <span className="customer-verification__field-value">{customer.carrier}</span>
        </div>
        <div className="customer-verification__field">
          <span className="customer-verification__field-label">Company Name</span>
          <span className="customer-verification__field-value">{customer.company_name ?? "—"}</span>
        </div>
        <div className="customer-verification__field">
          <span className="customer-verification__field-label">FRN</span>
          <span className="customer-verification__field-value">{rmdFrn || fccFrn || "—"}</span>
        </div>
      </div>

      <div className="customer-verification__tiles">
        <VerificationTile
          title="RMD Verification"
          verification={customer.rmd_verification}
          statusInfo={rmdVerificationStatusInfo}
          onSelectRecord={onSelectRmdRecord}
          onOpenRecord={onOpenRmdRecord}
          recordLabelField="business_name"
          recordNumberField="number"
          numberLabel="RMD Number"
          selectedRecordId={selectedRmdRecordId}
          candidatesOverride={rmdCandidatesOverride}
        />
        <VerificationTile
          title="FCC Verification"
          verification={customer.fcc_verification}
          statusInfo={fccVerificationStatusInfo}
          onSelectRecord={onSelectFccRecord}
          onOpenRecord={onOpenFccRecord}
          recordLabelField="legal_name"
          recordNumberField="filer_id"
          numberLabel="Filer ID"
          selectedRecordId={selectedFccRecordId}
          candidatesOverride={fccCandidatesOverride}
        />

        <div className="customer-verification-tile customer-verification-tile--static">
          <div className="customer-verification-tile__head">
            <span className="customer-verification-tile__title">FRN Match</span>
            <Badge tone={frnMatch.tone}>{frnMatch.label}</Badge>
          </div>
          <div className="customer-verification-tile__frn-row">
            <span>RMD FRN: {rmdFrn || "—"}</span>
            <span>FCC FRN: {fccFrn || "—"}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
