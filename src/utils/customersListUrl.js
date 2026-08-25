// Remembers the Customers list's own last URL (path + query string, so
// search term/compliance filter/page all round-trip) so "Back to
// Customers" from a customer's detail page returns to exactly where the
// person left off, instead of always resetting to a bare, empty list.
// sessionStorage (not app state) survives navigating away to the detail
// page and back without needing to lift this into a shared provider.
const STORAGE_KEY = "telecomply-customers-list-url";

export function saveCustomersListUrl(pathWithSearch) {
  try {
    sessionStorage.setItem(STORAGE_KEY, pathWithSearch);
  } catch {
    // Storage can be unavailable (private browsing, quota) -- losing the
    // remembered URL just means "Back to Customers" falls back to the
    // plain list, never a hard failure.
  }
}

export function getCustomersListUrl() {
  try {
    return sessionStorage.getItem(STORAGE_KEY) || "/customers";
  } catch {
    return "/customers";
  }
}
