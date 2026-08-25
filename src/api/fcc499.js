import { apiGet } from "./client";

export function fetchFcc499Stats() {
  return apiGet("/fcc/stats/");
}

export function searchFcc499(query, page = 1) {
  return apiGet("/fcc/search/", { query, page });
}

export function fetchFcc499Detail(id) {
  return apiGet(`/fcc/${id}/`);
}
