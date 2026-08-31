import { API_BASE_URL, apiGet, apiPost } from "./client";

export function fetchCustomerStats() {
  return apiGet("/customers/stats/");
}

export function listCustomers({ page = 1, pageSize, complianceStatus } = {}) {
  return apiGet("/customers/", { page, page_size: pageSize, compliance_status: complianceStatus });
}

export function searchCustomers({ carrier, page = 1, complianceStatus }) {
  return apiGet("/customers/search/", { carrier, page, compliance_status: complianceStatus });
}

export function fetchCustomerDetail(id, { rmdRecordId, fccRecordId } = {}) {
  return apiGet(`/customers/${id}/`, { rmd_record: rmdRecordId, fcc_record: fccRecordId });
}

export function createCustomer(carrier) {
  return apiPost("/customers/", { carrier });
}

// Persists which real RMD/FCC record is confirmed as this customer, so an
// ambiguous match stays resolved on every future visit (see
// CustomerDetail's "Save" action). Only the keys actually passed are
// touched -- pass null for a key to clear that side back to "ambiguous".
export function linkCustomerRecords(id, { rmdRecordId, fccRecordId } = {}) {
  const body = {};
  if (rmdRecordId !== undefined) body.rmd_record_id = rmdRecordId;
  if (fccRecordId !== undefined) body.fcc_record_id = fccRecordId;
  return apiPost(`/customers/${id}/link-records/`, body);
}

export function customerReportPdfUrl(id) {
  return `${API_BASE_URL}/customers/${id}/report/`;
}
