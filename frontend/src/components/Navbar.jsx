import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import ThemeToggle from './ThemeToggle';

export default function Navbar({ 
  title, 
  onRefresh, 
  mobileOpen, 
  setMobileOpen 
}) {
  const navigate = useNavigate();

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (e) {
      console.warn('Logout API call failed:', e);
    }
    localStorage.removeItem('fg_token');
    navigate('/login');
  };

  // Toggle sidebar on mobile
  const toggleSidebar = () => {
    setMobileOpen(!mobileOpen);
  };

  return (
    <header className="navbar">
      <div className="navbar-left">
        {/* Hamburger button – visible only on mobile */}
        <button 
          className="sidebar-toggle" 
          onClick={toggleSidebar}
          aria-label="Toggle sidebar"
        >
          ☰
        </button>
        <h1 className="page-title">{title}</h1>
        <span className="breadcrumb">FraudGuard / {title}</span>
      </div>
      <div className="navbar-right">
        <button className="icon-btn" onClick={onRefresh} title="Refresh">↺</button>
        <ThemeToggle />
        <div className="user-pill">
          <span className="user-avatar">👤</span>
          <span className="user-name">Analyst</span>
          <span className="dropdown-arrow">▾</span>
          <div className="dropdown">
            <button onClick={logout}>🚪 Logout</button>
          </div>
        </div>
      </div>
    </header>
  );
}