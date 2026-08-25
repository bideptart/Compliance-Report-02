import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Search, X, Loader2, ServerCrash, SearchX, UserPlus } from "lucide-react";
import PageHeader from "../components/PageHeader";
import Section from "../components/Section";
import EmptyState from "../components/EmptyState";
import Pagination from "../components/Pagination";
import CustomerResultsTable from "../components/CustomerResultsTable";
import CustomerFormPanel from "../components/CustomerFormPanel";
import { listCustomers, searchCustomers } from "../api/customers";
import { saveCustomersListUrl } from "../utils/customersListUrl";
import "../styles/page.css";
import "../components/Toolbar.css";
import "./Customers.css";

const PAGE_SIZE = 50;

const COMPLIANCE_STATUS_OPTIONS = [
  { value: "all", label: "All Customers" },
  { value: "fully_compliant", label: "Fully Compliant" },
  { value: "rmd_not_satisfied", label: "RMD Not Satisfied" },
  { value: "no_filer_id", label: "No Filer ID" },
  { value: "not_active", label: "Not Active" },
  { value: "foreign_voice_provider", label: "Foreign Voice Provider" },
  { value: "no_intermediate_registry", label: "No Intermediate Registry" },
];

export default function Customers() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Lets the Dashboard's compliance cards deep-link straight into a
  // filtered view (e.g. /customers?complianceStatus=rmd_not_satisfied), and
  // -- together with the effect below that writes every change back to the
  // URL -- lets this page's full state (search term, filter, page) survive
  // navigating to a customer's detail page and back via "Back to Customers"
  // (see utils/customersListUrl), instead of always resetting to a blank
  // first page. Only read once, on mount; the URL and this state stay in
  // sync from here on.
  const initialCarrier = searchParams.get("search");
  const initialComplianceStatus = (() => {
    const fromUrl = searchParams.get("complianceStatus");
    return COMPLIANCE_STATUS_OPTIONS.some((o) => o.value === fromUrl) ? fromUrl : "all";
  })();
  const initialPage = (() => {
    const fromUrl = parseInt(searchParams.get("page"), 10);
    return Number.isInteger(fromUrl) && fromUrl > 0 ? fromUrl : 1;
  })();

  const [carrierInput, setCarrierInput] = useState(initialCarrier ?? "");
  const [activeCarrier, setActiveCarrier] = useState(initialCarrier);
  const [complianceStatus, setComplianceStatus] = useState(initialComplianceStatus);
  const [page, setPage] = useState(initialPage);
  const [validationMessage, setValidationMessage] = useState(null);

  const [results, setResults] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [createOpen, setCreateOpen] = useState(false);

  const isSearching = activeCarrier !== null;

  // Loads either the full paginated Customer Database (activeCarrier ===
  // null) or filtered search results -- same table, same columns, so
  // clearing a search just switches this fetch back to browse mode. The
  // Compliance Status dropdown applies on top of either mode.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const request = isSearching
      ? searchCustomers({ carrier: activeCarrier, page, complianceStatus })
      : listCustomers({ page, complianceStatus });

    request
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
            : "Something went wrong while loading customer records."
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeCarrier, page, isSearching, complianceStatus]);

  // Keeps the URL (and, from there, the remembered "last customers URL" --
  // see utils/customersListUrl) in lockstep with every search/filter/page
  // change, `replace: true` so browsing pages within this list doesn't pile
  // up back-button history entries. This is what makes "Back to Customers"
  // land on the exact state the person left, not a fresh blank list.
  useEffect(() => {
    const params = {};
    if (activeCarrier) params.search = activeCarrier;
    if (complianceStatus !== "all") params.complianceStatus = complianceStatus;
    if (page > 1) params.page = String(page);
    setSearchParams(params, { replace: true });

    const query = new URLSearchParams(params).toString();
    saveCustomersListUrl(query ? `/customers?${query}` : "/customers");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCarrier, complianceStatus, page]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    const trimmed = carrierInput.trim();

    setValidationMessage(null);
    setPage(1);
    setActiveCarrier(trimmed || null);
  };

  const handleClearSearch = () => {
    setCarrierInput("");
    setValidationMessage(null);
    setPage(1);
    setActiveCarrier(null);
  };

  const handleComplianceStatusChange = (e) => {
    setPage(1);
    setComplianceStatus(e.target.value);
  };

  // Land straight on the new customer's own detail page -- that's where
  // its real RMD/FCC verification actually runs and shows up, not here.
  const handleCustomerCreated = (customer) => {
    setCreateOpen(false);
    navigate(`/customers/${customer.id}`);
  };

  // Clicking anywhere on a customer's row goes straight to that customer's
  // full compliance page -- there's no more inline verification panel on
  // this page to select a row into.
  const handleRowClick = (record) => {
    navigate(`/customers/${record.id}`);
  };

  const pageCount = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const complianceLabel = COMPLIANCE_STATUS_OPTIONS.find((o) => o.value === complianceStatus)?.label;

  const databaseDescription = isSearching
    ? `Search results for "${activeCarrier}"${complianceStatus !== "all" ? ` · ${complianceLabel}` : ""}`
    : complianceStatus !== "all"
      ? `Filtered by ${complianceLabel}`
      : "All customers stored in the compliance database";

  return (
    <div>
      <PageHeader
        title="Customers"
        actions={
          <button type="button" className="filter-button" onClick={() => setCreateOpen(true)}>
            <UserPlus size={15} />
            Create Customer
          </button>
        }
      />

      <Section title="Search Customers">
        <form className="customers-search" onSubmit={handleSearchSubmit}>
          <div className="customers-search__field">
            <label htmlFor="customer-carrier">Search Carrier</label>
            <input
              id="customer-carrier"
              type="text"
              placeholder="e.g. VX-Telecom GP"
              value={carrierInput}
              onChange={(e) => setCarrierInput(e.target.value)}
            />
          </div>
          <div className="customers-compliance-filter">
            <label htmlFor="compliance-status">Compliance Status</label>
            <select id="compliance-status" value={complianceStatus} onChange={handleComplianceStatusChange}>
              {COMPLIANCE_STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="customers-search__actions">
            <button type="submit" className="customers-search__button">
              <Search size={15} />
              Search
            </button>
            {isSearching && (
              <button type="button" className="customers-clear-button" onClick={handleClearSearch}>
                <X size={14} />
                Clear
              </button>
            )}
          </div>
        </form>
        {validationMessage && <p className="customers-search__validation">{validationMessage}</p>}
      </Section>

      <div style={{ height: 18 }} />

      <Section title="Customer Database" description={databaseDescription}>
        {loading && (
          <div className="customers-loading">
            <Loader2 size={22} className="customers-loading__spinner" />
            <span>Verifying customer records against RMD and FCC...</span>
          </div>
        )}

        {!loading && error && (
          <EmptyState icon={ServerCrash} title="Unable to load customer data" description={error} />
        )}

        {!loading && !error && results.length === 0 && (
          <EmptyState
            icon={SearchX}
            title="No matching records found"
            description={
              isSearching
                ? "Try a different carrier name."
                : complianceStatus !== "all"
                  ? "No customers match this compliance status."
                  : "No customers have been imported yet."
            }
          />
        )}

        {!loading && !error && results.length > 0 && (
          <>
            <CustomerResultsTable records={results} onRowClick={handleRowClick} />
            <Pagination page={page} pageCount={pageCount} totalCount={totalCount} onPageChange={setPage} />
          </>
        )}
      </Section>

      <CustomerFormPanel open={createOpen} onClose={() => setCreateOpen(false)} onSaved={handleCustomerCreated} />
    </div>
  );
}
