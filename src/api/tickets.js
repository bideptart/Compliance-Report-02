import { apiGet, apiPost, apiPatch } from "./client";

export function fetchTicketStats() {
  return apiGet("/tickets/stats/");
}

export function fetchTickets({ page = 1, search, status, dateFrom, dateTo, customerId } = {}) {
  return apiGet("/tickets/", {
    page,
    search,
    status,
    date_from: dateFrom,
    date_to: dateTo,
    customer: customerId,
  });
}

export function fetchTicketDetail(id) {
  return apiGet(`/tickets/${id}/`);
}

export function createTicket(fields) {
  return apiPost("/tickets/", fields);
}

export function updateTicket(id, fields) {
  return apiPatch(`/tickets/${id}/`, fields);
}
