import { useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header from "./Header";
import "./Layout.css";

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <div className={`app-shell__body ${collapsed ? "app-shell__body--collapsed" : ""}`}>
        <Header />
        <main className="app-shell__content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
