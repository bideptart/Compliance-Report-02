import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Network, CheckCircle2, XCircle, AlertTriangle, Loader2, ServerCrash, SearchX } from "lucide-react";
import PageHeader from "../components/PageHeader";
import Section from "../components/Section";
import EmptyState from "../components/EmptyState";
import Pagination from "../components/Pagination";
import Badge from "../components/Badge";
import { StatCard } from "../components/Card";
import RegistryDetailPanel from "../components/RegistryDetailPanel";
import EscalationFormPanel from "../components/EscalationFormPanel";
import {
  fetchRegistryStats,
  fetchRegistryRecords,
  fetchRegistryDetail,
  runRegistryCheck,
  updateEscalation,
} from "../api/intermediateRegistry";
import { registryStatusTone, formatDateTimeMDY } from "../utils/registryStatus";
import "../styles/page.css";
import "../components/RmdResultsTable.css";
import "../components/Toolbar.css";
import "./Customers.css";
import "./TroubleTickets.css";

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "present", label: "Present" },
  { value: "not_present", label: "Not Present" },
  { value: "review_required", label: "Review Required" },
];

const PAGE_SIZE = 25;

export default function IntermediateRegistry() {
  const navigate = useNavigate();

  const [stats, setStats] = useState(null);

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  const [records, setRecords] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);
  const [detailRecord, setDetailRecord] = useState(null);
  const [checking, setChecking] = useState(false);

  const [escalationFormOpen, setEscalationFormOpen] = useState(false);
  const [updatingEscalation, setUpdatingEscalation] = useState(false);

  const loadStats = () => {
    fetchRegistryStats()
      .then((data) => setStats(data))
      .catch(() => setStats(null));
  };

  const loadRecords = () => {
    setLoading(true);
    setError(null);

    fetchRegistryRecords({ page, search, status: statusFilter })
      .then((data) => {
        setRecords(data.results ?? []);
        setTotalCount(data.count ?? 0);
      })
      .catch((err) => {
        setRecords([]);
        setTotalCount(0);
        setError(
          err.status === 0
            ? "Cannot connect to the compliance server. Please make sure the backend is running."
            : "Something went wrong while loading the Intermediate Registry."
        );
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadStats();
  }, []);

  useEffect(() => {
    loadRecords();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, search, statusFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  };

  // Each summary card filters the table by exactly the real condition it
  // counts -- "Total Customers" clears the filter (it's the total), the
  // others set the one status value that matches their own count on the
  // backend (see intermediate_registry/views.py's RegistryStatsView).
  const applyCardFilter = (nextStatus) => {
    setPage(1);
    setStatusFilter(nextStatus ?? "");
  };

  const openDetail = (record) => {
    setDetailOpen(true);
    setDetailLoading(true);
    setDetailError(null);
    setDetailRecord(null);

    fetchRegistryDetail(record.id)
      .then((data) => setDetailRecord(data))
      .catch(() => setDetailError("Unable to load this registry record's details."))
      .finally(() => setDetailLoading(false));
  };

  const handleCheckNow = (record) => {
    setChecking(true);
    runRegistryCheck(record.id)
      .then((data) => {
        setDetailRecord(data);
        loadRecords();
        loadStats();
      })
      .catch(() => setDetailError("Unable to run the registry check for this customer. Please try again."))
      .finally(() => setChecking(false));
  };

  const handleViewCustomer = (record) => {
    navigate(`/customers/${record.customer}`);
  };

  const handleEscalate = () => {
    setEscalationFormOpen(true);
  };

  // A newly-created escalation always belongs to whichever registry
  // record is currently open in the detail panel -- re-fetching that
  // record's detail (rather than trusting the create response alone)
  // guarantees the panel reflects the real, saved active_escalation/
  // latest_escalation state exactly as the backend computed it.
  const handleEscalationCreated = () => {
    setEscalationFormOpen(false);
    if (detailRecord) openDetail(detailRecord);
    loadRecords();
  };

  const handleUpdateEscalationStatus = (escalation, newStatus) => {
    setUpdatingEscalation(true);
    updateEscalation(escalation.id, { status: newStatus })
      .then(() => {
        if (detailRecord) openDetail(detailRecord);
        loadRecords();
      })
      .catch(() => setDetailError("Unable to update this escalation. Please try again."))
      .finally(() => setUpdatingEscalation(false));
  };

  const pageCount = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const statValue = (key) => (stats?.[key] === undefined ? "0" : stats[key].toLocaleString());

  return (
    <div>
      <PageHeader
        title="Intermediate Registry"
        description="Whether each customer/vendor appears in the Intermediate Provider Registry."
      />

      <div className="stat-grid">
        <button type="button" className="dashboard-stat-link" onClick={() => applyCardFilter(null)}>
          <StatCard label="Total Customers" icon={Network} value={statValue("total_customers")} />
        </button>
        <button type="button" className="dashboard-stat-link" onClick={() => applyCardFilter("present")}>
          <StatCard label="Present" icon={CheckCircle2} tone="success" value={statValue("present")} />
        </button>
        <button type="button" className="dashboard-stat-link" onClick={() => applyCardFilter("not_present")}>
          <StatCard label="Not Present" icon={XCircle} tone="neutral" value={statValue("not_present")} />
        </button>
        <button type="button" className="dashboard-stat-link" onClick={() => applyCardFilter("review_required")}>
          <StatCard label="Review Required" icon={AlertTriangle} tone="warning" value={statValue("review_required")} />
        </button>
      </div>

      <Section title="Search & Filters">
        <form className="ticket-filters" onSubmit={handleSearchSubmit}>
          <div className="ticket-filters__search">
            <input
              type="text"
              placeholder="Search by customer/vendor name or Registry ID"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
            <button type="submit">Search</button>
          </div>

          <div className="ticket-filters__selects">
            <select
              value={statusFilter}
              onChange={(e) => {
                setPage(1);
                setStatusFilter(e.target.value);
              }}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </form>
      </Section>

      <div style={{ height: 18 }} />

      <Section title="Registry Records">
        {loading && (
          <div className="customers-loading">
            <Loader2 size={22} className="customers-loading__spinner" />
            <span>Loading registry records...</span>
          </div>
        )}

        {!loading && error && (
          <EmptyState icon={ServerCrash} title="Unable to load Intermediate Registry" description={error} />
        )}

        {!loading && !error && records.length === 0 && (
          <EmptyState
            icon={SearchX}
            title="No registry records found"
            description="Every real customer's Intermediate Provider Registry status will appear here."
          />
        )}

        {!loading && !error && records.length > 0 && (
          <>
            <div className="table-shell">
              <table className="rmd-results-table">
                <thead>
                  <tr>
                    <th>Registry ID</th>
                    <th>Customer/Vendor Name</th>
                    <th>Intermediate Registry Status</th>
                    <th>Change Status</th>
                    <th>Last Checked</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((r) => (
                    <tr key={r.id} className="ticket-table__row" onClick={() => openDetail(r)}>
                      <td className="rmd-results-table__business">{r.registry_id}</td>
                      <td>{r.customer_name}</td>
                      <td>
                        <Badge tone={registryStatusTone(r.status)}>{r.status_label}</Badge>
                      </td>
                      <td>
                        <Badge tone={r.change_detected ? "warning" : "neutral"}>
                          {r.change_detected ? "Changed" : "No Change"}
                        </Badge>
                      </td>
                      <td>{formatDateTimeMDY(r.last_checked)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageCount={pageCount} totalCount={totalCount} onPageChange={setPage} />
          </>
        )}
      </Section>

      <RegistryDetailPanel
        open={detailOpen}
        loading={detailLoading}
        error={detailError}
        record={detailRecord}
        checking={checking}
        onClose={() => setDetailOpen(false)}
        onCheckNow={handleCheckNow}
        onViewCustomer={handleViewCustomer}
        onEscalate={handleEscalate}
        onUpdateEscalationStatus={handleUpdateEscalationStatus}
        updatingEscalation={updatingEscalation}
      />

      <EscalationFormPanel
        open={escalationFormOpen}
        record={detailRecord}
        onClose={() => setEscalationFormOpen(false)}
        onCreated={handleEscalationCreated}
      />
    </div>
  );
}
