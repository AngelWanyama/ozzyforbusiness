import { NavLink, Outlet, useLocation } from 'react-router-dom';
import './Layout.css';

export default function Layout() {
  const location = useLocation();

  return (
    <div className="app-container">
      <Outlet />
      <nav className="bottom-nav">
        <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'active' : ''}>
          <span className="nav-icon">📊</span>
          <span>Dashboard</span>
        </NavLink>
        <NavLink to="/transactions" className={({ isActive }) => isActive ? 'active' : ''}>
          <span className="nav-icon">📋</span>
          <span>Transactions</span>
        </NavLink>
        <NavLink to="/inventory" className={({ isActive }) => isActive ? 'active' : ''}>
          <span className="nav-icon">📦</span>
          <span>Inventory</span>
        </NavLink>
        <NavLink to="/reports" className={({ isActive }) => isActive ? 'active' : ''}>
          <span className="nav-icon">📈</span>
          <span>Reports</span>
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => isActive ? 'active' : ''}>
          <span className="nav-icon">⚙️</span>
          <span>Settings</span>
        </NavLink>
      </nav>
    </div>
  );
}