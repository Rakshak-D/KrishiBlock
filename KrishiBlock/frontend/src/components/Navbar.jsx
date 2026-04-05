import { Link, NavLink, useNavigate } from "react-router-dom";
import { DatabaseZap, LogOut, MessageCircleMore, ShieldCheck } from "lucide-react";
import useAuthStore from "../store/authStore";

const NAV_ITEMS = [
  { to: "/", label: "Home", end: true },
  { to: "/market", label: "Marketplace" },
  { to: "/ledger", label: "Ledger" },
  { to: "/bot", label: "WhatsApp sim" },
];

export default function Navbar() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <header className="shell-nav shell-nav-clean">
      <Link className="brand" to="/">
        <img alt="KrishiBlock logo" className="brand-logo" src="/krishiblock-logo.svg" />
        <span>
          <strong>KrishiBlock</strong>
          <small>Verified agri-trade, escrow, ledger, and WhatsApp workflows</small>
        </span>
      </Link>

      <nav aria-label="Primary" className="nav-links">
        {NAV_ITEMS.map((item) => (
          <NavLink end={item.end} key={item.to} to={item.to}>
            {item.label}
          </NavLink>
        ))}
        <NavLink to={user ? "/dashboard" : "/login"}>{user ? "Workspace" : "Sign in"}</NavLink>
      </nav>

      <div className="nav-meta">
        <div className="nav-statuses mobile-hide">
          <span className="chip chip-soft">
            <ShieldCheck size={15} /> Public verify
          </span>
          <span className="chip chip-soft">
            <DatabaseZap size={15} /> Live chain
          </span>
          <span className="chip chip-soft">
            <MessageCircleMore size={15} /> WhatsApp ready
          </span>
        </div>
        {user ? (
          <div className="profile-chip">
            <button className="ghost-button slim-button" onClick={() => navigate("/dashboard")} type="button">
              {user.name?.split(" ")[0] || "Workspace"}
            </button>
            <button aria-label="Log out" className="ghost-button slim-icon-button" onClick={handleLogout} type="button">
              <LogOut size={15} />
            </button>
          </div>
        ) : (
          <button className="primary-button" onClick={() => navigate("/login")} type="button">
            Open workspace
          </button>
        )}
      </div>
    </header>
  );
}
