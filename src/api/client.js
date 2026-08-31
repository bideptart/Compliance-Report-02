// The Vite dev server (npm run dev) always talks to the local Django backend
// on :8000 -- see README's "Getting Started". A production build
// (import.meta.env.DEV === false) keeps calling the deployed backend, exactly
// as before; only local dev behavior changes here.
export const API_BASE_URL = import.meta.env.DEV ? "http://localhost:8000/api" : "https://compliance-report-02.onrender.com/api";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiGet(path, params = {}) {
  const url = new URL(`${API_BASE_URL}${path}`);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, value);
    }
  });

  let response;
  try {
    response = await fetch(url.toString());
  } catch {
    throw new ApiError("Unable to reach the server. Please check your connection.", 0);
  }

  if (!response.ok) {
    throw new ApiError(`Request failed with status ${response.status}`, response.status);
  }

  return response.json();
}

export async function apiDelete(path) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { method: "DELETE" });
  } catch {
    throw new ApiError("Unable to reach the server. Please check your connection.", 0);
  }

  if (!response.ok) {
    throw new ApiError(`Request failed with status ${response.status}`, response.status);
  }

  return response.json();
}

// For multipart uploads (e.g. a KYC document file) -- pass a FormData
// instance directly, never JSON-encoded, so the file survives the request.
export async function apiPostForm(path, formData) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { method: "POST", body: formData });
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
    const message =
      detail && typeof detail === "object"
        ? Object.values(detail).flat().join(" ")
        : `Request failed with status ${response.status}`;
    throw new ApiError(message || `Request failed with status ${response.status}`, response.status);
  }

  return response.json();
}

async function _apiJsonRequest(method, path, body) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
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
    const message =
      detail && typeof detail === "object"
        ? Object.values(detail).flat().join(" ")
        : `Request failed with status ${response.status}`;
    throw new ApiError(message || `Request failed with status ${response.status}`, response.status);
  }

  return response.json();
}

// For plain-JSON creates/updates (no file involved) -- e.g. Trouble Tickets.
export function apiPost(path, body) {
  return _apiJsonRequest("POST", path, body);
}

export function apiPatch(path, body) {
  return _apiJsonRequest("PATCH", path, body);
}
