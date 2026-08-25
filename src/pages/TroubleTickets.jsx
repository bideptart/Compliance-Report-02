import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  TicketPlus,
  Loader2,
  ServerCrash,
  TicketX,
  ListChecks,
  CircleDot,
  Clock,
  CheckCircle2,
} from "lucide-react";
import PageHeader from "../components/PageHeader";
import Section from "../components/Section";
import EmptyState from "../components/EmptyState";
import Pagination from "../components/Pagination";
import Badge from "../components/Badge";
import { StatCard } from "../components/Card";
import TicketFormPanel from "../components/TicketFormPanel";
import TicketDetailPanel from "../components/TicketDetailPanel";
import { listCustomers } from "../api/customers";
import { fetchTickets, fetchTicketStats, fetchTicketDetail, updateTicket } from "../api/tickets";
import { ticketStatusTone, formatDateMDY } from "../utils/ticketStatus";
import "../styles/page.css";
import "./Customers.css";
import "../components/RmdResultsTable.css";
import "../components/Toolbar.css";
import "./TroubleTickets.css";

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In Progress" },
  { value: "resolved", label: "Resolved" },
  { value: "closed", label: "Closed" },
];

const STATUS_LABELS = Object.fromEntries(STATUS_OPTIONS.filter((o) => o.value).map((o) => [o.value, o.label]));

const PAGE_SIZE = 25;

export default function TroubleTickets() {
  const [searchParams] = useSearchParams();

  // Lets the Dashboard's ticket summary deep-link straight into a filtered
  // view (e.g. /trouble-tickets?status=open) -- only read once, on mount.
  const initialStatus = (() => {
    const fromUrl = searchParams.get("status");
    return STATUS_OPTIONS.some((o) => o.value === fromUrl) ? fromUrl : "";
  })();

  const [customers, setCustomers] = useState([]);
  const [stats, setStats] = useState(null);

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState(initialStatus);
  const [page, setPage] = useState(1);

  const [tickets, setTickets] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState("create");
  const [formTicket, setFormTicket] = useState(null);

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);
  const [detailTicket, setDetailTicket] = useState(null);

  const loadStats = () => {
    fetchTicketStats()
      .then((data) => setStats(data))
      .catch(() => setStats(null));
  };

  const loadTickets = () => {
    setLoading(true);
    setError(null);

    fetchTickets({ page, search, status })
      .then((data) => {
        setTickets(data.results ?? []);
        setTotalCount(data.count ?? 0);
      })
      .catch((err) => {
        setTickets([]);
        setTotalCount(0);
        setError(
          err.status === 0
            ? "Cannot connect to the compliance server. Please make sure the backend is running."
            : "Something went wrong while loading trouble tickets."
        );
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    listCustomers({ page: 1, pageSize: 200 })
      .then((data) => setCustomers(data.results ?? []))
      .catch(() => setCustomers([]));
    loadStats();
  }, []);

  useEffect(() => {
    loadTickets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, search, status]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  };

  const refreshAfterChange = () => {
    loadTickets();
    loadStats();
  };

  const openCreate = () => {
    setFormMode("create");
    setFormTicket(null);
    setFormOpen(true);
  };

  const openEdit = (ticket) => {
    setFormMode("edit");
    setFormTicket(ticket);
    setFormOpen(true);
    setDetailOpen(false);
  };

  const openView = (ticket) => {
    setDetailOpen(true);
    setDetailLoading(true);
    setDetailError(null);
    setDetailTicket(null);

    fetchTicketDetail(ticket.id)
      .then((data) => setDetailTicket(data))
      .catch(() => setDetailError("Unable to load this ticket's details."))
      .finally(() => setDetailLoading(false));
  };

  const handleSaved = () => {
    setFormOpen(false);
    refreshAfterChange();
  };

  const handleCloseTicket = (ticket) => {
    const today = new Date();
    const iso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(
      today.getDate()
    ).padStart(2, "0")}`;

    updateTicket(ticket.id, { status: "closed", date_closed: ticket.date_closed || iso }).then((saved) => {
      setDetailTicket(saved);
      refreshAfterChange();
    });
  };

  const pageCount = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const statValue = (key) => (stats?.[key] === undefined ? "0" : stats[key].toLocaleString());

  return (
    <div>
      <PageHeader
        title="Trouble Tickets"
        description="Track, manage, and resolve customer issues."
        actions={
          <button type="button" className="filter-button" onClick={openCreate}>
            <TicketPlus size={15} />
            Create Ticket
          </button>
        }
      />

      <div className="stat-grid">
        <StatCard label="Total Tickets" icon={ListChecks} value={statValue("total")} />
        <StatCard label="Open" icon={CircleDot} tone="danger" value={statValue("open")} />
        <StatCard label="In Progress" icon={Clock} tone="warning" value={statValue("in_progress")} />
        <StatCard label="Closed" icon={CheckCircle2} tone="success" value={statValue("closed")} />
      </div>

      <Section title="Search & Filters">
        <form className="ticket-filters" onSubmit={handleSearchSubmit}>
          <div className="ticket-filters__search">
            <input
              type="text"
              placeholder="Search by Ticket Number or Customer"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
            <button type="submit">Search</button>
          </div>

          <div className="ticket-filters__selects">
            <select
              value={status}
              onChange={(e) => {
                setPage(1);
                setStatus(e.target.value);
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

      <Section title="Trouble Tickets">
        {loading && (
          <div className="customers-loading">
            <Loader2 size={22} className="customers-loading__spinner" />
            <span>Loading trouble tickets...</span>
          </div>
        )}

        {!loading && error && <EmptyState icon={ServerCrash} title="Unable to load trouble tickets" description={error} />}

        {!loading && !error && tickets.length === 0 && (
          <div className="ticket-empty">
            <EmptyState
              icon={TicketX}
              title="No trouble tickets available yet."
              description="Create a ticket to start tracking customer issues."
            />
            <button type="button" className="filter-button ticket-empty__cta" onClick={openCreate}>
              <TicketPlus size={15} />
              Create Ticket
            </button>
          </div>
        )}

        {!loading && !error && tickets.length > 0 && (
          <>
            <div className="table-shell">
              <table className="rmd-results-table">
                <thead>
                  <tr>
                    <th>Ticket Number</th>
                    <th>Customer</th>
                    <th>Date Opened</th>
                    <th>Status</th>
                    <th>NOC Notified</th>
                    <th>Customer Notified</th>
                    <th>Date Closed</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((t) => (
                    <tr key={t.id} className="ticket-table__row" onClick={() => openView(t)}>
                      <td className="rmd-results-table__business">{t.ticket_number}</td>
                      <td>{t.customer_name}</td>
                      <td>{formatDateMDY(t.date_opened)}</td>
                      <td>
                        <Badge tone={ticketStatusTone(t.status)}>{STATUS_LABELS[t.status] ?? t.status_label}</Badge>
                      </td>
                      <td>{t.noc_notified ? "Yes" : "No"}</td>
                      <td>{t.customer_notified ? "Yes" : "No"}</td>
                      <td>{formatDateMDY(t.date_closed)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageCount={pageCount} totalCount={totalCount} onPageChange={setPage} />
          </>
        )}
      </Section>

      <TicketFormPanel
        open={formOpen}
        mode={formMode}
        ticket={formTicket}
        customers={customers}
        onClose={() => setFormOpen(false)}
        onSaved={handleSaved}
      />

      <TicketDetailPanel
        open={detailOpen}
        loading={detailLoading}
        error={detailError}
        ticket={detailTicket}
        onClose={() => setDetailOpen(false)}
        onEdit={openEdit}
        onCloseTicket={handleCloseTicket}
      />
    </div>
  );
}
