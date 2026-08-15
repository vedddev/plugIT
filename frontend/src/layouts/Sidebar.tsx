import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  ListOrdered,
  Server,
  Boxes,
  KeyRound,
  BarChart3,
  Settings as SettingsIcon,
  Activity,
} from "lucide-react";

const navItems = [
  { to: "/overview", label: "Overview", icon: LayoutDashboard },
  { to: "/requests", label: "Requests", icon: ListOrdered },
  { to: "/providers", label: "Providers", icon: Server },
  { to: "/models", label: "Models", icon: Boxes },
  { to: "/api-keys", label: "API Keys", icon: KeyRound },
  { to: "/usage", label: "Usage", icon: BarChart3 },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export function Sidebar() {
  return (
    <aside className="sidebar" aria-label="Primary navigation">
      <div className="sidebar__brand">
        <div className="sidebar__logo">S</div>
        <div className="sidebar__wordmark">
          <span className="sidebar__name">SmartLLM</span>
          <span className="sidebar__sub">Admin Console</span>
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
      </nav>
      <div className="sidebar__footer">
        <div className="sidebar__status">
          <Activity size={14} className="sidebar__icon" />
          <div>
            <div className="sidebar__status-label">System status</div>
            <div className="sidebar__status-value">Local gateway</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
