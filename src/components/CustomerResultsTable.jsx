import { Link } from "react-router-dom";
import Badge from "./Badge";
import { customerFrnMatchInfo, operationalStatusInfo } from "../utils/rmdStatus";
import { registryStatusTone } from "../utils/registryStatus";
import "./RmdResultsTable.css";

export default function CustomerResultsTable({ records, selectedId, onRowClick }) {
  return (
    <div className="table-shell">
      <table className="rmd-results-table">
        <thead>
          <tr>
            <th>Carrier Name</th>
            <th>Country of Origin</th>
            <th>Filer ID</th>
            <th>FRN</th>
            <th>Operational Status</th>
            <th>KYC Status</th>
            <th>FSF Status</th>
            <th>FRN Status</th>
            <th>IPR</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record) => {
            const frnStatus = customerFrnMatchInfo(record.frn_verification?.status);
            const operationalStatus = operationalStatusInfo(record.operational_status);
            const frn = record.rmd_verification?.frn || record.fcc_verification?.frn;

            return (
              <tr
                key={record.id}
                className={
                  "rmd-results-table__row" +
                  (record.id === selectedId ? " rmd-results-table__row--selected" : "")
                }
                onClick={onRowClick ? () => onRowClick(record) : undefined}
              >
                <td className="rmd-results-table__business">
                  <Link
                    to={`/customers/${record.id}`}
                    className="rmd-results-table__link-name"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {record.carrier ?? "Not Available"}
                  </Link>
                </td>
                <td>{record.country ?? "Not Available"}</td>
                <td>
                  {record.filer_id ? (
                    <Badge tone="success">{record.filer_id}</Badge>
                  ) : (
                    <Badge tone="neutral">Not Available</Badge>
                  )}
                </td>
                <td>
                  {frn ? <Badge tone="success">{frn}</Badge> : <Badge tone="neutral">Not Available</Badge>}
                </td>
                <td>
                  {record.operational_status ? (
                    <Badge tone={operationalStatus.tone}>{operationalStatus.label}</Badge>
                  ) : (
                    <Badge tone="neutral">Not Available</Badge>
                  )}
                </td>
                <td>
                  {/* No real KYC verification-status model exists yet
                      (separate from uploaded KYC documents, which do have a
                      backend). Never show a fabricated status here. */}
                  <Badge tone="neutral">Not Available</Badge>
                </td>
                <td>
                  {/* FSF (signed deal form between both parties) has no
                      backend/data source yet -- placeholder until that's
                      built. Never show a fabricated status here. */}
                  <Badge tone="neutral">Not Available</Badge>
                </td>
                <td>
                  <Badge tone={frnStatus.tone}>{frnStatus.label}</Badge>
                </td>
                <td>
                  {record.intermediate_registry_status ? (
                    <Badge tone={registryStatusTone(record.intermediate_registry_status)}>
                      {record.intermediate_registry_status_label}
                    </Badge>
                  ) : (
                    <Badge tone="neutral">Not Available</Badge>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
