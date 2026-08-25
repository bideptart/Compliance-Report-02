import { apiGet, apiPostForm } from "./client";

export function fetchDocuments({ page = 1, customerId, documentType } = {}) {
  return apiGet("/documents/", { page, customer: customerId, document_type: documentType });
}

export function uploadDocuments({ customerId, files, documentType }) {
  const formData = new FormData();
  formData.append("customer", customerId);
  if (documentType) formData.append("document_type", documentType);
  Array.from(files).forEach((file) => formData.append("files", file));
  return apiPostForm("/documents/", formData);
}
