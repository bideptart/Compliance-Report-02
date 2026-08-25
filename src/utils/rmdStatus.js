export const OPERATIONAL_STATUS_LABELS = {
  active: { label: "Active", tone: "success" },
  inactive: { label: "Inactive", tone: "danger" },
  unknown: { label: "Unknown", tone: "neutral" },
};

export const FRN_MATCH_LABELS = {
  matched: { label: "Matched", tone: "success" },
  mismatch: { label: "Unmatched", tone: "danger" },
  not_available: { label: "Unmatched", tone: "danger" },
  verification_required: { label: "Verification Required", tone: "warning" },
};

export function operationalStatusInfo(value) {
  return OPERATIONAL_STATUS_LABELS[value] ?? OPERATIONAL_STATUS_LABELS.unknown;
}

export function frnMatchInfo(value) {
  return FRN_MATCH_LABELS[value] ?? FRN_MATCH_LABELS.not_available;
}

export const RMD_VERIFICATION_STATUS_LABELS = {
  present: { label: "Present in RMD", tone: "success" },
  not_present: { label: "Not Present in RMD", tone: "danger" },
  multiple_matches: { label: "Multiple Matches / Review Required", tone: "warning" },
  verification_pending: { label: "Verification Pending", tone: "neutral" },
  verification_error: { label: "Verification Error", tone: "danger" },
};

export function rmdVerificationStatusInfo(value) {
  return RMD_VERIFICATION_STATUS_LABELS[value] ?? RMD_VERIFICATION_STATUS_LABELS.not_present;
}

export const FCC_VERIFICATION_STATUS_LABELS = {
  present: { label: "Present in FCC", tone: "success" },
  not_present: { label: "Not Present in FCC", tone: "danger" },
  multiple_matches: { label: "Multiple Matches / Review Required", tone: "warning" },
  verification_pending: { label: "Not in FCC", tone: "danger" },
  verification_error: { label: "Verification Error", tone: "danger" },
};

export function fccVerificationStatusInfo(value) {
  return FCC_VERIFICATION_STATUS_LABELS[value] ?? FCC_VERIFICATION_STATUS_LABELS.not_present;
}

// FRN match label used specifically by the Customers module -- same
// statuses as frnMatchInfo, but an unresolved company match reads as
// "Unmatched" here instead of "Verification Required" (the RMD/FCC pages
// keep the longer wording since it's more precise about *why*).
export function customerFrnMatchInfo(value) {
  if (value === "verification_required") {
    return { label: "Unmatched", tone: "danger" };
  }
  return frnMatchInfo(value);
}

// Short "Verified ✓"-style label used specifically on the combined Customer
// Verification card (the RMD/FCC pages keep their own longer wording).
export function shortVerifiedStatusInfo(value) {
  const map = {
    present: { label: "Verified", tone: "success" },
    not_present: { label: "Not Verified", tone: "danger" },
    multiple_matches: { label: "Review Required", tone: "warning" },
    verification_pending: { label: "Not Verified", tone: "neutral" },
    verification_error: { label: "Error", tone: "danger" },
  };
  return map[value] ?? map.not_present;
}
