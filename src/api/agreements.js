import { apiGet, apiPostForm } from "./client";
import { API_BASE_URL, ApiError } from "./client";

export function fetchAgreementStats() {
  return apiGet("/agreements/stats/");
}

export function fetchAgreements({ page = 1, search, agreementType, status, expiryPeriod, customerId } = {}) {
  return apiGet("/agreements/", {
    page,
    search,
    agreement_type: agreementType,
    status,
    expiry_period: expiryPeriod,
    customer: customerId,
  });
}

export function fetchAgreementDetail(id) {
  return apiGet(`/agreements/${id}/`);
}

function buildAgreementFormData({ customerId, agreementTitle, agreementType, status, effectiveDate, expiryDate, autoRenewal, document, notes }) {
  const formData = new FormData();
  if (customerId !== undefined) formData.append("customer", customerId);
  if (agreementTitle !== undefined) formData.append("agreement_title", agreementTitle);
  if (agreementType !== undefined) formData.append("agreement_type", agreementType);
  if (status !== undefined) formData.append("status", status);
  if (effectiveDate !== undefined) formData.append("effective_date", effectiveDate);
  if (expiryDate) formData.append("expiry_date", expiryDate);
  if (autoRenewal !== undefined) formData.append("auto_renewal", autoRenewal ? "true" : "false");
  if (document) formData.append("document", document);
  if (notes !== undefined) formData.append("notes", notes || "");
  return formData;
}

export function createAgreement(fields) {
  return apiPostForm("/agreements/", buildAgreementFormData(fields));
}

// PATCH with a multipart body -- apiPostForm always POSTs, so this issues
// its own fetch with method: "PATCH" instead.
export async function updateAgreement(id, fields) {
  const formData = buildAgreementFormData(fields);
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/agreements/${id}/`, { method: "PATCH", body: formData });
  } catch {
    throw new ApiError("Unable to reach the server. Please check your connection.", 0);
  }
  if (!response.ok) {
    let detail;
    try {
      detail = await response.json();
    } catch {
      detail = null;
    }
    const message = detail && typeof detail === "object" ? Object.values(detail).flat().join(" ") : `Request failed with status ${response.status}`;
    throw new ApiError(message || `Request failed with status ${response.status}`, response.status);
  }
  return response.json();
}

export function renewAgreement(id, { effectiveDate, expiryDate, agreementTitle, agreementType, autoRenewal, document, notes }) {
  const formData = new FormData();
  formData.append("effective_date", effectiveDate);
  if (expiryDate) formData.append("expiry_date", expiryDate);
  if (agreementTitle) formData.append("agreement_title", agreementTitle);
  if (agreementType) formData.append("agreement_type", agreementType);
  if (autoRenewal !== undefined) formData.append("auto_renewal", autoRenewal ? "true" : "false");
  if (document) formData.append("document", document);
  if (notes !== undefined) formData.append("notes", notes || "");
  return apiPostForm(`/agreements/${id}/renew/`, formData);
}

export function terminateAgreement(id, terminationReason) {
  const formData = new FormData();
  if (terminationReason) formData.append("termination_reason", terminationReason);
  return apiPostForm(`/agreements/${id}/terminate/`, formData);
}
