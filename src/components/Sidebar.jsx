import { NavLink, useNavigate } from "react-router-dom";
import { ShieldCheck, ChevronsLeft, ChevronsRight } from "lucide-react";
import { NAV_ITEMS } from "../config/navigation";
import { getCustomersListUrl } from "../utils/customersListUrl";
import "./Sidebar.css";

export default function Sidebar({ collapsed, onToggle }) {
  const navigate = useNavigate();

  // The Customers nav item deep-links to whatever search/filter/page the
  // person last left the Customers list on (see utils/customersListUrl)
  // instead of a bare "/customers" -- otherwise every click back into
  // Customers from the sidebar silently resets the Compliance Status
  // filter to "All Customers", even though nothing about it was ever
  // changed. Resolved with an onClick (not a precomputed `to`) because
  // Sidebar has no reason to re-render just from a filter change on the
  // Customers page itself (it reads no router/customers state), so a
  // `to` prop set once at render time can go stale; reading
  // getCustomersListUrl() at the moment of the actual click is always
  // current regardless of Sidebar's own render timing.
  const handleCustomersClick = (e) => {
    e.preventDefault();
    navigate(getCustomersListUrl());
  };

  return (
    <aside className={`sidebar ${collapsed ? "sidebar--collapsed" : ""}`}>
      <div className="sidebar__brand">
        <div className="sidebar__brand-icon">
          <ShieldCheck size={22} strokeWidth={2.25} />
        </div>
        {!collapsed && (
          <div className="sidebar__brand-text">
            <span className="sidebar__brand-title">TeleComply</span>
            <span className="sidebar__brand-subtitle">Compliance Suite</span>
          </div>
        )}
      </div>

      <nav className="sidebar__nav">
        {NAV_ITEMS.map(({ label, path, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path === "/"}
            onClick={path === "/customers" ? handleCustomersClick : undefined}
            className={({ isActive }) =>
              `sidebar__link ${isActive ? "sidebar__link--active" : ""}`
            }
            title={collapsed ? label : undefined}
          >
            <span className="sidebar__link-icon">
              <Icon size={19} strokeWidth={2} />
            </span>
            {!collapsed && <span className="sidebar__link-label">{label}</span>}
          </NavLink>
        ))}
      </nav>

      <button
        type="button"
        className="sidebar__toggle"
        onClick={onToggle}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? <ChevronsRight size={18} /> : <ChevronsLeft size={18} />}
        {!collapsed && <span>Collapse</span>}
      </button>
    </aside>
  );
}
