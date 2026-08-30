import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { useWebSocket } from "../hooks/useWebSocket.js";
import Logo from "../components/Logo.jsx";
import { StatusDot } from "../components/common/index.jsx";

const NAV = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/batch", label: "Batch Upload" },
  { to: "/feed", label: "Live Feed" },
  { to: "/audit", label: "Audit Trail" },
  { to: "/halted", label: "Halted Actions" },
  { to: "/exceptions", label: "Exceptions" },
];

export default function AppLayout() {
  const { session, signOut } = useAuth();
  const navigate = useNavigate();
  // One socket for the whole shell so the sidebar's LIVE indicator and every
  // screen share a single connection.
  const { connected } = useWebSocket();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <Logo size={26} variant="dark" />
          <StatusDot on={connected} />
        </div>
        <nav className="sidebar-nav">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) => `nav-item ${isActive ? "nav-active" : ""}`}
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <NavLink
            to="/settings"
            className={({ isActive }) => `nav-item ${isActive ? "nav-active" : ""}`}
          >
            Settings
          </NavLink>
          <div className="sidebar-user">
            <span className="mono dim">{session?.email}</span>
            <button
              className="linkish mono"
              onClick={() => {
                signOut();
                navigate("/");
              }}
            >
              Sign out
            </button>
          </div>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}

export function PageHeader({ title, meta, actions }) {
  return (
    <header className="page-head">
      <div>
        <h1 className="page-title">{title}</h1>
        {meta && <div className="page-meta mono dim">{meta}</div>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}
