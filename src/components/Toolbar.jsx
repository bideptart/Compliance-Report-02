import { Search, SlidersHorizontal } from "lucide-react";
import "./Toolbar.css";

export function SearchInput({ placeholder = "Search..." }) {
  return (
    <div className="search-input">
      <Search size={16} className="search-input__icon" />
      <input type="text" placeholder={placeholder} />
    </div>
  );
}

export function FilterButton({ label = "Filters" }) {
  return (
    <button type="button" className="filter-button">
      <SlidersHorizontal size={15} />
      {label}
    </button>
  );
}

export function Toolbar({ children }) {
  return <div className="toolbar">{children}</div>;
}
