import { Bell, Moon, Sun, UserCircle } from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import "./Header.css";

// Always the app name, never the current page's title -- the page itself
// (see PageHeader) already shows that, so this stays constant across every
// route instead of duplicating it.
export default function Header() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <header className="header">
      <div className="header__title">
        <h1>TeleComply</h1>
      </div>

      <div className="header__actions">
        <button
          type="button"
          role="switch"
          aria-checked={isDark}
          className={"theme-toggle" + (isDark ? " theme-toggle--dark" : "")}
          aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
          onClick={toggleTheme}
        >
          <Sun size={13} className="theme-toggle__icon theme-toggle__icon--sun" />
          <Moon size={13} className="theme-toggle__icon theme-toggle__icon--moon" />
          <span className="theme-toggle__thumb">
            {isDark ? <Moon size={12} /> : <Sun size={12} />}
          </span>
        </button>
        <button type="button" className="header__icon-btn" aria-label="Notifications">
          <Bell size={19} />
        </button>
        <div className="header__divider" />
        <div className="header__user">
          <UserCircle size={28} strokeWidth={1.5} />
          <div className="header__user-info">
            <span className="header__user-name">Compliance Admin</span>
            <span className="header__user-role">Administrator</span>
          </div>
        </div>
      </div>
    </header>
  );
}
