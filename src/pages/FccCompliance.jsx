import { useEffect, useState } from "react";
import { Search, Loader2, ServerCrash, SearchX, History, RefreshCw } from "lucide-react";
import PageHeader from "../components/PageHeader";
import Section from "../components/Section";
import EmptyState from "../components/EmptyState";
import Pagination from "../components/Pagination";
import FccResultsTable from "../components/FccResultsTable";
import FccDetailPanel from "../components/FccDetailPanel";
import { searchFcc499, fetchFcc499Detail } from "../api/fcc499";
import { useFccHistory } from "../context/FccHistoryContext";
import "../styles/page.css";
import "./Rmd.css";

const PAGE_SIZE = 25;

// Builds a Search History row from the full record shown in the filing info
// panel -- history only gets an entry once a record has actually been opened.
function toHistoryRow(detail) {
  return {
    id: detail.id,
    filer_id: detail.filer_id,
    legal_name: detail.legal_name,
    cores_id: detail.cores_id,
    operational_status: detail.operational_status,
    detail_url: detail.detail_url,
    rmd_verification: detail.rmd_verification,
    frn_verification: detail.frn_verification,
  };
}

export default function FccCompliance() {
  const [companyInput, setCompanyInput] = useState("");
  const [activeCompany, setActiveCompany] = useState(null);
  const [page, setPage] = useState(1);
  const [validationMessage, setValidationMessage] = useState(null);

  const [results, setResults] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [selectedId, setSelectedId] = useState(null);
  const [detailRecord, setDetailRecord] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);

  const { history, addSearchResults, refreshHistory, refreshing, refreshError } = useFccHistory();

  useEffect(() => {
    if (activeCompany === null) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    searchFcc499(activeCompany, page)
      .then((data) => {
        if (cancelled) return;
        setResults(data.results ?? []);
        setTotalCount(data.count ?? 0);

        const meta = data.meta;
        if (meta && meta.status !== "ok" && (data.results ?? []).length === 0) {
          if (meta.status === "not_found") {
            setError(null);
          } else {
            setError(meta.message || "Something went wrong while checking the FCC Form 499 source.");
          }
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setResults([]);
        setTotalCount(0);
        setError(
          err.status === 0
            ? "Cannot connect to the compliance server. Please make sure the backend is running."
            : "Something went wrong while searching FCC Form 499 records."
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeCompany, page]);

  const closeSearchResults = () => {
    setActiveCompany(null);
    setResults([]);
    setTotalCount(0);
    setError(null);
    setLoading(false);
    setPage(1);
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    const trimmed = companyInput.trim();

    if (!trimmed) {
      setValidationMessage("Enter a company name to search.");
      return;
    }

    setValidationMessage(null);
    setPage(1);
    setActiveCompany(trimmed);
  };

  const handleRefresh = () => {
    setCompanyInput("");
    setValidationMessage(null);
    closeSearchResults();
    if (history.length > 0) refreshHistory();
  };

  // Clicking a company name opens its full filing info panel and, once that
  // real record loads, records it in Search History. The results list stays
  // on screen -- it only goes away once the user clicks Refresh.
  const handleOpenSearchResult = (record) => {
    setSelectedId(record.id);
    setDetailRecord(null);
    setDetailError(null);
    setDetailLoading(true);

    fetchFcc499Detail(record.id)
      .then((data) => {
        setDetailRecord(data);
        addSearchResults([toHistoryRow(data)], `Company: ${record.legal_name ?? ""}`);
      })
      .catch(() => setDetailError("Unable to load this record's details."))
      .finally(() => setDetailLoading(false));
  };

  const handleOpenHistoryEntry = (record) => {
    setSelectedId(record.id);
    setDetailRecord(null);
    setDetailError(null);
    setDetailLoading(true);

    fetchFcc499Detail(record.id)
      .then((data) => setDetailRecord(data))
      .catch(() => setDetailError("Unable to load this record's details."))
      .finally(() => setDetailLoading(false));
  };

  const pageCount = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const hasSearched = activeCompany !== null;

  return (
    <div>
      <PageHeader title="FCC Compliance" />

      <Section title="Search FCC Form 499 Filings">
        <form className="rmd-search" onSubmit={handleSearchSubmit}>
          <div className="rmd-search__field">
            <label htmlFor="fcc-company">Company Name</label>
            <input
              id="fcc-company"
              type="text"
              placeholder="e.g. Ajoxi Limited"
              value={companyInput}
              onChange={(e) => setCompanyInput(e.target.value)}
            />
          </div>
          <div className="rmd-search__actions">
            <button type="submit" className="rmd-search__button">
              <Search size={15} />
              Search FCC
            </button>
            <button
              type="button"
              className="rmd-refresh-button"
              onClick={handleRefresh}
              disabled={refreshing}
            >
              <RefreshCw size={14} className={refreshing ? "rmd-refresh-button__spin" : undefined} />
              {refreshing ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </form>
        {validationMessage && <p className="rmd-search__validation">{validationMessage}</p>}
        {refreshError && <p className="rmd-search__validation">{refreshError}</p>}
      </Section>

      {hasSearched && (
        <>
          <div style={{ height: 18 }} />

          <Section title="Search Results">
            {loading && (
              <div className="rmd-loading">
                <Loader2 size={22} className="rmd-loading__spinner" />
                <span>Checking FCC Form 499 records...</span>
              </div>
            )}

            {!loading && error && (
              <EmptyState icon={ServerCrash} title="Unable to search FCC data" description={error} />
            )}

            {!loading && !error && results.length === 0 && (
              <EmptyState
                icon={SearchX}
                title="No matching records found"
                description="Try a different company name, or check the exact legal name registered with the FCC."
              />
            )}

            {!loading && !error && results.length > 0 && (
              <>
                <FccResultsTable records={results} onRowClick={handleOpenSearchResult} />
                <Pagination
                  page={page}
                  pageCount={pageCount}
                  totalCount={totalCount}
                  onPageChange={setPage}
                />
              </>
            )}
          </Section>
        </>
      )}

      <div style={{ height: 18 }} />

      <Section title="Search History" description="Records you have viewed during this session">
        {history.length === 0 ? (
          <EmptyState
            icon={History}
            title="No search history yet"
            description="Open a filing's info panel from your search results to add it here."
          />
        ) : (
          <FccResultsTable records={history} showSearchedAt onRowClick={handleOpenHistoryEntry} />
        )}
      </Section>

      <FccDetailPanel
        open={selectedId !== null}
        loading={detailLoading}
        error={detailError}
        record={detailRecord}
        onClose={() => setSelectedId(null)}
      />
    </div>
  );
}
