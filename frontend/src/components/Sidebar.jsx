import { useState, useEffect } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';

// Helper to decode JWT token and get role
const getUserRole = () => {
  const token = localStorage.getItem('fg_token');
  if (!token) return 'analyst';
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    const payload = JSON.parse(jsonPayload);
    return payload.role || 'analyst';
  } catch (e) {
    console.warn('Invalid token, defaulting to analyst');
    return 'analyst';
  }
};

const navItems = [
  { to: '/', label: 'Live Feed', icon: '📡', badge: 'live' },
  { to: '/approval', label: 'Approval Queue', icon: '⚖️', badge: 'count' },
  { to: '/history', label: 'History', icon: '📋' },
  { to: '/predict', label: 'Predict', icon: '🔍' },
  { to: '/batch', label: 'Batch Analysis', icon: '📁' },
  { to: '/model', label: 'Model Info', icon: '🧠' },
  { to: '/admin', label: 'Admin Panel', icon: '🛡️', admin: true },
];

export default function Sidebar({ collapsed, setCollapsed }) {
  const location = useLocation();
  const navigate = useNavigate();  // <-- useNavigate for admin
  const [pendingCount, setPendingCount] = useState(0);
  const userRole = getUserRole();

  useEffect(() => {
    const interval = setInterval(() => {}, 30000);
    return () => clearInterval(interval);
  }, []);

  const filteredNavItems = navItems.filter(
    (item) => !item.admin || (item.admin && userRole === 'admin')
  );

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="brand">
          <span className="shield">🛡️</span>
          <span className="brand-name">FraudGuard</span>
          <span className="version">v3</span>
        </div>
        <button className="collapse-btn" onClick={() => setCollapsed(!collapsed)}>
          {collapsed ? '→' : '←'}
        </button>
      </div>

      <nav className="sidebar-nav">
        {filteredNavItems.map((item) => {
          // For admin, we use a button with navigate to ensure client-side routing
          if (item.to === '/admin') {
            return (
              <button
                key={item.to}
                className={`nav-item ${location.pathname === '/admin' ? 'active' : ''}`}
                onClick={() => navigate('/admin')}
              >
                <span className="icon">{item.icon}</span>
                <span className="label">{item.label}</span>
                {item.badge && item.badge === 'live' && <span className="badge live">●</span>}
                {item.badge && item.badge === 'count' && <span className="badge count">{pendingCount}</span>}
              </button>
            );
          }

          // All other items use NavLink
          let badgeContent = null;
          if (item.badge === 'live') {
            badgeContent = <span className="badge live">●</span>;
          } else if (item.badge === 'count') {
            badgeContent = <span className="badge count">{pendingCount}</span>;
          }
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <span className="icon">{item.icon}</span>
              <span className="label">{item.label}</span>
              {badgeContent}
            </NavLink>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="status">
          <span className="dot"></span>
          <span>System Online</span>
        </div>
        <div className="refresh-timer">Next refresh in 30s</div>
      </div>
    </aside>
  );
}