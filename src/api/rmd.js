import { API_BASE_URL, apiGet } from "./client";

export function listRmd({ page = 1, pageSize } = {}) {
  return apiGet("/rmd/", { page, page_size: pageSize });
}

export function searchRmd({ company, frn, ocn, page = 1 }) {
  return apiGet("/rmd/search/", { company, frn, ocn, page });
}

export function fetchRmdDetail(id) {
  return apiGet(`/rmd/${id}/`);
}

export function rmdDownloadUrl(id) {
  return `${API_BASE_URL}/rmd/${id}/download/`;
}
