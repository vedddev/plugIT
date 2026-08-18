import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Bot,
  ListOrdered,
  Server,
  Boxes,
  KeyRound,
  BarChart3,
  Settings as SettingsIcon,
  BookOpen, LogOut, UserRound,
} from "lucide-react";
import { useAuth } from "../services/AuthContext";
import { getUserDisplayName, getUserInitials } from "../services/user";

const navItems = [
  { to: "/playground", label: "Playground", icon: Bot },
  { to: "/api-keys", label: "API Keys", icon: KeyRound },
  { to: "/models", label: "Models", icon: Boxes },
  { to: "/usage", label: "Usage", icon: BarChart3 },
  { to: "/requests", label: "Requests", icon: ListOrdered },
  { to: "/overview", label: "Overview", icon: LayoutDashboard },
  { to: "/providers", label: "Providers", icon: Server },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export function Sidebar() {
  const { user, signOut } = useAuth();
  return (
    <aside className="sidebar" aria-label="Primary navigation">
      <div className="sidebar__brand">
        <div className="sidebar__logo">R</div>
        <div className="sidebar__wordmark">
          <span className="sidebar__name">RIM</span>
          <span className="sidebar__sub">ADMIN CONSOLE</span>
        </div>
      </div>
      <nav className="sidebar__nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `sidebar__link${isActive ? " sidebar__link--active" : ""}`
              }
            >
              <Icon size={16} className="sidebar__icon" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
        <a className="sidebar__link" href="/docs" target="_blank" rel="noreferrer">
          <BookOpen size={16} className="sidebar__icon" />
          <span>Documentation</span>
        </a>
      </nav>
      <div className="sidebar__footer">
        {user && <div className="sidebar__profile">
          <span className="sidebar__avatar"><UserRound size={14} /></span>
          <div className="sidebar__profile-copy"><strong>{getUserDisplayName(user)}</strong><span>{user.email}</span></div>
        </div>}
        <button className="sidebar__logout" type="button" onClick={() => void signOut()}>
          <LogOut size={15} /> Log out
        </button>
        <div className="sidebar__status">
          <span className="sidebar__status-dot" />
          <span className="sidebar__status-value">Gateway online</span>
        </div>
      </div>
    </aside>
  );
}
