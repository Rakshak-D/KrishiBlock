import { Link, NavLink, useNavigate } from "react-router-dom";
import { DatabaseZap, LogOut, ShieldCheck, Sprout } from "lucide-react";
import useAuthStore from "../store/authStore";

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
        <span className="brand-mark">
          <Sprout size={18} />
        </span>
        <span>
          <strong>AgriChain</strong>
          <small>Trade, escrow, verify, and trust ledger</small>
        </span>
      </Link>

      <nav className="nav-links">
        <NavLink to="/">Home</NavLink>
        <NavLink to="/market">Marketplace</NavLink>
        <NavLink to="/ledger">Trust ledger</NavLink>
        <NavLink to="/bot">Console</NavLink>
        {user ? <NavLink to="/dashboard">Workspace</NavLink> : <NavLink to="/login">Sign in</NavLink>}
      </nav>

      <div className="nav-meta">
        <span className="chip chip-soft mobile-hide">
          <ShieldCheck size={15} /> Public verify
        </span>
        <span className="chip chip-soft mobile-hide">
          <DatabaseZap size={15} /> Chain explorer
        </span>
        {user ? (
          <div className="profile-chip">
            <button className="ghost-button slim-button" onClick={() => navigate("/dashboard")} type="button">
              {user.name?.split(" ")[0] || "Workspace"}
            </button>
            <button aria-label="Log out" className="ghost-button slim-icon-button" onClick={handleLogout} type="button">
              <LogOut size={15} />
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}

