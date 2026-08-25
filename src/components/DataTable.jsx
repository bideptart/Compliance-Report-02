import EmptyState from "./EmptyState";
import { Inbox } from "lucide-react";

export default function DataTable({ columns, emptyTitle, emptyDescription }) {
  return (
    <div className="table-shell">
      <table>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr className="table-empty-row">
            <td colSpan={columns.length}>
              <EmptyState
                icon={Inbox}
                title={emptyTitle ?? "No data available yet"}
                description={emptyDescription}
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
