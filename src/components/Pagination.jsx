import { ChevronLeft, ChevronRight } from "lucide-react";
import "./Pagination.css";

export default function Pagination({ page, pageCount, totalCount, onPageChange }) {
  if (!totalCount) return null;

  return (
    <div className="pagination">
      <span className="pagination__summary">
        Page {page} of {pageCount} &middot; {totalCount} total records
      </span>
      <div className="pagination__controls">
        <button
          type="button"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          aria-label="Previous page"
        >
          <ChevronLeft size={16} />
        </button>
        <button
          type="button"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pageCount}
          aria-label="Next page"
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}
