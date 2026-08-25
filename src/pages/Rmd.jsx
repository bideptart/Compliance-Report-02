import { useEffect, useState } from "react";
import { Search, Loader2, ServerCrash, SearchX, History, RefreshCw } from "lucide-react";
import PageHeader from "../components/PageHeader";
import Section from "../components/Section";
import EmptyState from "../components/EmptyState";
import Pagination from "../components/Pagination";
import RmdResultsTable from "../components/RmdResultsTable";
import RmdDetailPanel from "../components/RmdDetailPanel";
import { searchRmd, fetchRmdDetail } from "../api/rmd";
import { useRmdHistory } from "../context/RmdHistoryContext";
import "../styles/page.css";
import "./Rmd.css";

const PAGE_SIZE = 25;

// Builds a Search History row from the full record shown in the business
// info panel -- deliberately not the same shape as a search-result row,
// since history only gets an entry once a record has actually been opened.
function toHistoryRow(detail) {
  return {
    id: detail.id,
    business_name: detail.business_name,
    country_of_origin: detail.country,
    frn: detail.frn,
    operational_status: detail.operational_status,
    frn_verification: detail.frn_verification,
    filing_url: detail.filing_url,
  };
}

export default function Rmd() {
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

  const { history, addSearchResults, refreshHistory, refreshing, refreshError } = useRmdHistory();

  useEffect(() => {
    if (activeCompany === null) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    searchRmd({ company: activeCompany, page })
      .then((data) => {
        if (cancelled) return;
        setResults(data.results ?? []);
        setTotalCount(data.count ?? 0);
      })
      .catch((err) => {
        if (cancelled) return;
        setResults([]);
        setTotalCount(0);
        setError(
          err.status === 0
            ? "Cannot connect to the compliance server. Please make sure the backend is running."
            : "Something went wrong while searching RMD records."
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

  // Clicking a business name opens its full info panel and, once that real
  // record loads, records it in Search History. The results list stays on
  // screen -- it only goes away once the user clicks Refresh.
  const handleOpenSearchResult = (record) => {
    setSelectedId(record.id);
    setDetailRecord(null);
    setDetailError(null);
    setDetailLoading(true);

    fetchRmdDetail(record.id)
      .then((data) => {
        setDetailRecord(data);
        addSearchResults([toHistoryRow(data)], `Company: ${record.business_name ?? ""}`);
      })
      .catch(() => setDetailError("Unable to load this record's details."))
      .finally(() => setDetailLoading(false));
  };

  const handleOpenHistoryEntry = (record) => {
    setSelectedId(record.id);
    setDetailRecord(null);
    setDetailError(null);
    setDetailLoading(true);

    fetchRmdDetail(record.id)
      .then((data) => setDetailRecord(data))
      .catch(() => setDetailError("Unable to load this record's details."))
      .finally(() => setDetailLoading(false));
  };

  const pageCount = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const hasSearched = activeCompany !== null;

  return (
    <div>
      <PageHeader title="Robocall Mitigation Database" />

      <Section title="Search RMD Filings">
        <form className="rmd-search" onSubmit={handleSearchSubmit}>
          <div className="rmd-search__field">
            <label htmlFor="rmd-company">Company Name</label>
            <input
              id="rmd-company"
              type="text"
              placeholder="e.g. Acme Telecom LLC"
              value={companyInput}
              onChange={(e) => setCompanyInput(e.target.value)}
            />
          </div>
          <div className="rmd-search__actions">
            <button type="submit" className="rmd-search__button">
              <Search size={15} />
              Search RMD
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
                <span>Searching RMD records...</span>
              </div>
            )}

            {!loading && error && (
              <EmptyState icon={ServerCrash} title="Unable to search RMD data" description={error} />
            )}

            {!loading && !error && results.length === 0 && (
              <EmptyState
                icon={SearchX}
                title="No matching records found"
                description="Try a different company name."
              />
            )}

            {!loading && !error && results.length > 0 && (
              <>
                <RmdResultsTable records={results} onRowClick={handleOpenSearchResult} />
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
            description="Open a business's info panel from your search results to add it here."
          />
        ) : (
          <RmdResultsTable records={history} showSearchedAt onRowClick={handleOpenHistoryEntry} />
        )}
      </Section>

      <RmdDetailPanel
        open={selectedId !== null}
        loading={detailLoading}
        error={detailError}
        record={detailRecord}
        onClose={() => setSelectedId(null)}
      />
    </div>
  );
}
