import { createContext, useCallback, useContext, useState } from "react";
import { fetchFcc499Detail } from "../api/fcc499";

const FccHistoryContext = createContext(null);

const MAX_HISTORY_ENTRIES = 50;

export function FccHistoryProvider({ children }) {
  const [history, setHistory] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState(null);

  // Records an FCC filing actually returned by the Django API. De-dupes by
  // record id so repeat searches move the entry to the top instead of piling
  // up duplicates, and never stores anything beyond what the backend sent.
  const addSearchResults = useCallback((records, searchTerms) => {
    if (!records || records.length === 0) return;

    setHistory((prev) => {
      const searchedAt = new Date().toISOString();
      const incoming = records.map((record) => ({
        ...record,
        searchTerms,
        searchedAt,
      }));
      const incomingIds = new Set(incoming.map((r) => r.id));
      const rest = prev.filter((entry) => !incomingIds.has(entry.id));
      return [...incoming, ...rest].slice(0, MAX_HISTORY_ENTRIES);
    });
  }, []);

  const clearHistory = useCallback(() => setHistory([]), []);

  // Re-fetches each history entry's real record from Django so the table
  // reflects the current database/RMD state, instead of caching a stale copy.
  const refreshHistory = useCallback(async () => {
    if (history.length === 0) return;

    setRefreshing(true);
    setRefreshError(null);

    try {
      const fresh = await Promise.all(
        history.map((entry) => fetchFcc499Detail(entry.id).catch(() => null))
      );
      setHistory((latest) =>
        latest.map((entry) => {
          const updated = fresh.find((f) => f && f.id === entry.id);
          if (!updated) return entry;
          return {
            ...entry,
            legal_name: updated.legal_name,
            cores_id: updated.cores_id,
            operational_status: updated.operational_status,
            detail_url: updated.detail_url,
            rmd_verification: updated.rmd_verification,
            frn_verification: updated.frn_verification,
          };
        })
      );
    } catch {
      setRefreshError("Unable to refresh search history from the server.");
    } finally {
      setRefreshing(false);
    }
  }, [history]);

  return (
    <FccHistoryContext.Provider
      value={{ history, addSearchResults, clearHistory, refreshHistory, refreshing, refreshError }}
    >
      {children}
    </FccHistoryContext.Provider>
  );
}

export function useFccHistory() {
  const ctx = useContext(FccHistoryContext);
  if (!ctx) {
    throw new Error("useFccHistory must be used within an FccHistoryProvider");
  }
  return ctx;
}
