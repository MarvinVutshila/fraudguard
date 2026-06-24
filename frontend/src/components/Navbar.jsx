import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import ThemeToggle from './ThemeToggle';

export default function Navbar({ title, onRefresh }) {
  const navigate = useNavigate();

  const logout = async () => {
    try {
      // Call the logout endpoint to record the event
      await api.post('/auth/logout');
    } catch (e) {
      console.warn('Logout API call failed:', e);
    }
    // Remove token and redirect to login regardless
    localStorage.removeItem('fg_token');
    navigate('/login');
  };

  return (
    <header className="navbar">
      <div className="navbar-left">
        <h1 className="page-title">{title}</h1>
        <span className="breadcrumb">FraudGuard / {title}</span>
      </div>
      <div className="navbar-right">
        <button className="icon-btn" onClick={onRefresh} title="Refresh">↺</button>
        {/* ThemeToggle component added here */}
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
