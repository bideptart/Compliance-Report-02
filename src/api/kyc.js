import { apiGet, apiPostForm } from "./client";

export function fetchKycDocuments({ page = 1, customerId } = {}) {
  return apiGet("/kyc/documents/", { page, customer: customerId });
}

export function fetchKycStats() {
  return apiGet("/kyc/stats/");
}

export function uploadKycDocument({ customerId, file }) {
  const formData = new FormData();
  formData.append("customer", customerId);
  formData.append("file", file);
  return apiPostForm("/kyc/documents/", formData);
}
