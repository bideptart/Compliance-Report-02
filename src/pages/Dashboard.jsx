import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  FileWarning,
  PowerOff,
  Globe,
  AlertCircle,
  Loader2,
  ServerCrash,
  FileSignature,
  Activity,
  Trash2,
  Network,
} from "lucide-react";
import PageHeader from "../components/PageHeader";
import { StatCard } from "../components/Card";
import Section from "../components/Section";
import EmptyState from "../components/EmptyState";
import Badge from "../components/Badge";
import ComplianceDistributionChart from "../components/ComplianceDistributionChart";
import { fetchCustomerStats } from "../api/customers";
import { fetchTicketStats } from "../api/tickets";
import { fetchAgreements } from "../api/agreements";
import { agreementStatusTone, formatDateMDY } from "../utils/agreementStatus";
import { clearRecentActivity, fetchRecentActivity } from "../api/dashboard";
import "../styles/page.css";
import "../components/RmdResultsTable.css";
import "./Dashboard.css";

// Same conditions as the Customers list's Compliance Status dropdown --
// every count here is computed fresh from the real Customer/RMD/FCC data
// (see /api/customers/stats/), never a stored or hardcoded number.
const COMPLIANCE_STATS = [
  { key: "fully_compliant", label: "Fully Compliant", icon: ShieldCheck, tone: "success" },
  { key: "rmd_not_satisfied", label: "RMD Not Satisfied", icon: ShieldAlert, tone: "danger" },
  { key: "no_filer_id", label: "No Filer ID", icon: FileWarning, tone: "warning" },
  { key: "not_active", label: "Not Active", icon: PowerOff, tone: "danger" },
  { key: "foreign_voice_provider", label: "Foreign Voice Provider", icon: Globe, tone: "neutral" },
  { key: "no_intermediate_registry", label: "No Intermediate Registry", icon: Network, tone: "warning" },
];

const TICKET_STATS = [
  { key: "total", label: "Total", tone: "primary" },
  { key: "open", label: "Open", tone: "danger" },
  { key: "in_progress", label: "In Progress", tone: "warning" },
  { key: "resolved", label: "Resolved", tone: "success" },
  { key: "closed", label: "Closed", tone: "neutral" },
];

function formatRelativeTime(isoTimestamp) {
  const then = new Date(isoTimestamp).getTime();
  const diffMs = Date.now() - then;
  const minutes = Math.round(diffMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

export default function Dashboard() {
  const navigate = useNavigate();

  const [stats, setStats] = useState(null);
  const [ticketStats, setTicketStats] = useState(null);
  const [activity, setActivity] = useState(null);
  const [activityError, setActivityError] = useState(null);
  const [clearingActivity, setClearingActivity] = useState(false);

  const [agreementAlerts, setAgreementAlerts] = useState(null);
  const [agreementAlertsError, setAgreementAlertsError] = useState(null);

  const loadActivity = () => {
    fetchRecentActivity(8)
      .then((data) => setActivity(data.results ?? []))
      .catch(() => {
        setActivity([]);
        setActivityError("Unable to load recent activity.");
      });
  };

  const handleClearActivity = () => {
    setClearingActivity(true);
    clearRecentActivity()
      .then(() => loadActivity())
      .catch(() => setActivityError("Unable to clear recent activity."))
      .finally(() => setClearingActivity(false));
  };

  useEffect(() => {
    let cancelled = false;

    fetchCustomerStats()
      .then((data) => !cancelled && setStats(data))
      .catch(() => !cancelled && setStats({}));

    fetchTicketStats()
      .then((data) => !cancelled && setTicketStats(data))
      .catch(() => !cancelled && setTicketStats({}));

    fetchRecentActivity(8)
      .then((data) => !cancelled && setActivity(data.results ?? []))
      .catch(() => {
        if (cancelled) return;
        setActivity([]);
        setActivityError("Unable to load recent activity.");
      });

    // Reuses the same Agreement list endpoint + status logic the Agreement
    // management UI (inside Customer Detail) already uses -- "expired" and
    // "expiring_soon" are computed server-side by Agreement.compute_status,
    // never recalculated here. Two small requests (each already filtered
    // and paginated by the backend) instead of one new endpoint.
    Promise.all([
      fetchAgreements({ status: "expired", page: 1 }),
      fetchAgreements({ status: "expiring_soon", page: 1 }),
    ])
      .then(([expired, expiringSoon]) => {
        if (cancelled) return;
        const merged = [...(expired.results ?? []), ...(expiringSoon.results ?? [])];
        merged.sort((a, b) => (a.expiry_date || "").localeCompare(b.expiry_date || ""));
        setAgreementAlerts(merged.slice(0, 5));
      })
      .catch(() => {
        if (cancelled) return;
        setAgreementAlerts([]);
        setAgreementAlertsError("Unable to load agreement alerts.");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const valueFor = (key) => (stats?.[key] === undefined ? "—" : stats[key].toLocaleString());
  const totalCustomers = stats?.total ?? 0;
  const ticketValueFor = (key) => (ticketStats?.[key] === undefined ? "—" : ticketStats[key].toLocaleString());

  const distributionItems = COMPLIANCE_STATS.map(({ key, label, tone }) => ({
    key,
    label,
    tone,
    value: stats?.[key] ?? 0,
  }));

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Monitor customer compliance, verification status, and operational activity."
      />

      <div className="stat-grid stat-grid--compact">
        {COMPLIANCE_STATS.map(({ key, label, icon: Icon, tone }) => (
          <Link key={key} to={`/customers?complianceStatus=${key}`} className="dashboard-stat-link">
            <StatCard
              label={label}
              icon={Icon}
              tone={tone}
              value={valueFor(key)}
              hint={stats ? `of ${valueFor("total")} customers` : undefined}
              progress={stats && totalCustomers > 0 ? ((stats[key] ?? 0) / totalCustomers) * 100 : undefined}
            />
          </Link>
        ))}
      </div>

      <div className="dashboard-two-col">
        <Section title="Compliance Distribution" description="Share of the customer base in each compliance condition">
          {stats ? (
            <ComplianceDistributionChart items={distributionItems} total={totalCustomers} />
          ) : (
            <div className="dashboard-loading">
              <Loader2 size={20} className="dashboard-loading__spinner" />
            </div>
          )}
        </Section>

        <Section
          title="Trouble Tickets"
          description="Current ticket workload"
          actions={
            <Link to="/trouble-tickets" className="dashboard-section-link">
              View All Tickets <ArrowRight size={13} />
            </Link>
          }
        >
          <div className="ticket-overview">
            {TICKET_STATS.map(({ key, label, tone }) => (
              <Link
                key={key}
                to={key === "total" ? "/trouble-tickets" : `/trouble-tickets?status=${key}`}
                className="ticket-overview__item"
              >
                <span className={`ticket-overview__value ticket-overview__value--${tone}`}>
                  {ticketValueFor(key)}
                </span>
                <span className="ticket-overview__label">{label}</span>
              </Link>
            ))}
          </div>
        </Section>
      </div>

      <div style={{ height: 18 }} />

      <Section title="Agreements Requiring Attention" description="Agreements that are expired or expiring soon">
        {agreementAlerts === null && !agreementAlertsError && (
          <div className="dashboard-loading">
            <Loader2 size={20} className="dashboard-loading__spinner" />
          </div>
        )}

        {agreementAlertsError && (
          <EmptyState icon={ServerCrash} title="Unable to load" description={agreementAlertsError} />
        )}

        {agreementAlerts !== null && !agreementAlertsError && agreementAlerts.length === 0 && (
          <EmptyState
            icon={FileSignature}
            title="No agreements require attention."
            description="Every agreement on file is active and not close to expiring."
          />
        )}

        {agreementAlerts !== null && !agreementAlertsError && agreementAlerts.length > 0 && (
          <div className="table-shell">
            <table className="rmd-results-table">
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Agreement ID</th>
                  <th>Status</th>
                  <th>Expiry Date</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {agreementAlerts.map((agreement) => (
                  <tr
                    key={agreement.id}
                    className="dashboard-table__row"
                    onClick={() => navigate(`/customers/${agreement.customer}`)}
                  >
                    <td className="rmd-results-table__business">{agreement.customer_name}</td>
                    <td>{agreement.agreement_id}</td>
                    <td>
                      <Badge tone={agreementStatusTone(agreement.status)}>{agreement.status_label}</Badge>
                    </td>
                    <td>{formatDateMDY(agreement.expiry_date)}</td>
                    <td>
                      <Link
                        to={`/customers/${agreement.customer}`}
                        className="dashboard-section-link"
                        onClick={(e) => e.stopPropagation()}
                      >
                        View <ArrowRight size={13} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <div style={{ height: 18 }} />

      <Section
        title="Recent Activity"
        description="Real events from Customers, Trouble Tickets, Agreements, Documents, and KYC"
        actions={
          activity !== null &&
          activity.length > 0 && (
            <button
              type="button"
              className="dashboard-section-link"
              onClick={handleClearActivity}
              disabled={clearingActivity}
            >
              {clearingActivity ? "Clearing..." : "Clear"} <Trash2 size={13} />
            </button>
          )
        }
      >
        {activity === null && !activityError && (
          <div className="dashboard-loading">
            <Loader2 size={20} className="dashboard-loading__spinner" />
          </div>
        )}

        {activityError && <EmptyState icon={ServerCrash} title="Unable to load" description={activityError} />}

        {activity !== null && !activityError && activity.length === 0 && (
          <EmptyState
            icon={Activity}
            title="No recent activity available."
            description="Activity will appear here as tickets, agreements, and documents are created."
          />
        )}

        {activity !== null && !activityError && activity.length > 0 && (
          <div className="activity-list">
            {activity.map((item, index) => (
              <div key={index} className="activity-list__item">
                <span className="activity-list__icon">
                  <AlertCircle size={15} />
                </span>
                <div className="activity-list__body">
                  <span className="activity-list__description">{item.description}</span>
                  <div className="activity-list__meta">
                    <Badge tone="neutral">{item.module}</Badge>
                    <span className="activity-list__time">{formatRelativeTime(item.timestamp)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}
