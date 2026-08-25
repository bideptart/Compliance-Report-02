import { ExternalLink } from "lucide-react";
import Badge from "./Badge";
import { frnMatchInfo, operationalStatusInfo, rmdVerificationStatusInfo } from "../utils/rmdStatus";
import "./RmdResultsTable.css";

function formatTimestamp(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  return date.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function FccResultsTable({ records, showSearchedAt = false, onRowClick }) {
  return (
    <div className="table-shell">
      <table className="rmd-results-table">
        <thead>
          <tr>
            <th>Company Name</th>
            <th>Filer ID</th>
            <th>FCC FRN</th>
            <th>Operational Status</th>
            <th>RMD Status</th>
            <th>FRN Match Status</th>
            <th>Official Link</th>
            {showSearchedAt && <th>Searched At</th>}
          </tr>
        </thead>
        <tbody>
          {records.map((record) => {
            const rmdStatus = rmdVerificationStatusInfo(record.rmd_verification?.status);
            const frnStatus = frnMatchInfo(record.frn_verification?.status);
            const operationalStatus = operationalStatusInfo(record.operational_status);

            return (
              <tr
                key={`${record.id}-${record.searchedAt ?? "current"}`}
                className={onRowClick ? "rmd-results-table__row" : undefined}
                onClick={onRowClick ? () => onRowClick(record) : undefined}
              >
                <td className="rmd-results-table__business">{record.legal_name ?? "—"}</td>
                <td>{record.filer_id ? <Badge tone="success">{record.filer_id}</Badge> : "—"}</td>
                <td>{record.cores_id ? <Badge tone="success">{record.cores_id}</Badge> : "—"}</td>
                <td>
                  <Badge tone={operationalStatus.tone}>{operationalStatus.label}</Badge>
                </td>
                <td>
                  <Badge tone={rmdStatus.tone}>{rmdStatus.label}</Badge>
                </td>
                <td>
                  <Badge tone={frnStatus.tone}>{frnStatus.label}</Badge>
                </td>
                <td>
                  {record.detail_url ? (
                    <a
                      className="rmd-results-table__link"
                      href={record.detail_url}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                    >
                      View Official FCC Record
                      <ExternalLink size={13} />
                    </a>
                  ) : (
                    "—"
                  )}
                </td>
                {showSearchedAt && <td>{formatTimestamp(record.searchedAt)}</td>}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
