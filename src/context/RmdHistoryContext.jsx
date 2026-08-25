import { createContext, useCallback, useContext, useState } from "react";
import { fetchRmdDetail } from "../api/rmd";

const RmdHistoryContext = createContext(null);

const MAX_HISTORY_ENTRIES = 50;

export function RmdHistoryProvider({ children }) {
  const [history, setHistory] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState(null);

  // Records a search result actually returned by the Django API. De-dupes by
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
  // reflects the current database state, instead of caching a stale copy.
  const refreshHistory = useCallback(async () => {
    if (history.length === 0) return;

    setRefreshing(true);
    setRefreshError(null);

    try {
      const fresh = await Promise.all(
        history.map((entry) => fetchRmdDetail(entry.id).catch(() => null))
      );
      setHistory((latest) =>
        latest.map((entry) => {
          const updated = fresh.find((f) => f && f.id === entry.id);
          if (!updated) return entry;
          return {
            ...entry,
            business_name: updated.business_name,
            country_of_origin: updated.country,
            frn: updated.frn,
            operational_status: updated.operational_status,
            filing_url: updated.filing_url,
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
    <RmdHistoryContext.Provider
      value={{ history, addSearchResults, clearHistory, refreshHistory, refreshing, refreshError }}
    >
      {children}
    </RmdHistoryContext.Provider>
  );
}

export function useRmdHistory() {
  const ctx = useContext(RmdHistoryContext);
  if (!ctx) {
    throw new Error("useRmdHistory must be used within an RmdHistoryProvider");
  }
  return ctx;
}
