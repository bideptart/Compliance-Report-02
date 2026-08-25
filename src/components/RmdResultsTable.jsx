import { ExternalLink } from "lucide-react";
import Badge from "./Badge";
import { frnMatchInfo } from "../utils/rmdStatus";
import "./RmdResultsTable.css";

function formatTimestamp(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  return date.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function RmdResultsTable({ records, showSearchedAt = false, onRowClick }) {
  return (
    <div className="table-shell">
      <table className="rmd-results-table">
        <thead>
          <tr>
            <th>Company Name</th>
            <th>Country of Origin</th>
            <th>FRN</th>
            <th>RMD and FCC Match</th>
            <th>Official Link</th>
            {showSearchedAt && <th>Searched At</th>}
          </tr>
        </thead>
        <tbody>
          {records.map((record) => {
            const match = frnMatchInfo(record.frn_verification?.status);

            return (
              <tr
                key={`${record.id}-${record.searchedAt ?? "current"}`}
                className={onRowClick ? "rmd-results-table__row" : undefined}
                onClick={onRowClick ? () => onRowClick(record) : undefined}
              >
                <td className="rmd-results-table__business">{record.business_name ?? "—"}</td>
                <td>{record.country_of_origin ?? "—"}</td>
                <td>{record.frn ? <Badge tone="success">{record.frn}</Badge> : "—"}</td>
                <td>
                  <Badge tone={match.tone}>{match.label}</Badge>
                </td>
                <td>
                  {record.filing_url ? (
                    <a
                      className="rmd-results-table__link"
                      href={record.filing_url}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                    >
                      View Official Site
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
