import { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faUsers, faUserCheck, faHourglassHalf, faLock, faFire,
  faExclamationTriangle, faUser, faShieldAlt, faBell,
  faSync, faClipboardList, faUserPlus, faEye
} from '@fortawesome/free-solid-svg-icons';
import {
  getPendingUsers,
  getUserStats,
  getSecurityAlerts,
  getLoginLogs,
  getUsers,
  approveUser,
  blockUser,
  unblockUser,
  deleteUser
} from '../services/api';
import StatusBadge from '../components/StatusBadge';
import '../styles/admin.css';

export default function AdminPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [users, setUsers] = useState([]);
  const [pending, setPending] = useState([]);
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

const fetchData = async () => {
  setLoading(true);
  setError(null);
  try {
    const [statsRes, usersRes, pendingRes, alertsRes, logsRes] = await Promise.all([
      getUserStats(),
      getUsers({ page: 1, page_size: 50 }),
      getPendingUsers(),
      getSecurityAlerts(),
      getLoginLogs({ limit: 20 })
    ]);

    setStats(statsRes.data);
    setUsers(usersRes.data?.users || []);
    setPending(pendingRes.data?.pending || []);   // ✅ fixed
    setAlerts(alertsRes.data?.alerts || []);
    setLogs(logsRes.data?.logs || []);             // ✅ fixed
  } catch (err) {
    console.error('Failed to fetch admin data:', err);
    setError('Failed to load admin data');
  } finally {
    setLoading(false);
  }
};

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleApprove = async (userId, approve) => {
    try {
      await approveUser(userId, approve);
      fetchData();
    } catch (err) {
      alert('Failed to update user');
    }
  };

  // 🛡️ Protect admin users from being blocked
  const handleBlock = async (user) => {
    if (user.role === 'admin') {
      alert('⚠️ Admin users cannot be blocked for security reasons.');
      return;
    }
    if (window.confirm(`Are you sure you want to block @${user.username}?`)) {
      try {
        await blockUser(user.id);
        fetchData();
      } catch (err) {
        alert('Failed to block user');
      }
    }
  };

  const handleUnblock = async (userId) => {
    try {
      await unblockUser(userId);
      fetchData();
    } catch (err) {
      alert('Failed to unblock user');
    }
  };

  const handleDelete = async (user) => {
    if (user.role === 'admin') {
      alert('⚠️ Admin users cannot be deleted for security reasons.');
      return;
    }
    if (window.confirm(`Are you sure you want to delete @${user.username}? This action cannot be undone.`)) {
      try {
        await deleteUser(user.id);
        fetchData();
      } catch (err) {
        alert('Failed to delete user');
      }
    }
  };

const statItems = [
  { key: 'total_users', label: 'Total Users', value: stats?.total_users || 0, icon: faUsers, color: 'blue' },
  { key: 'active_users', label: 'Active Users', value: stats?.active_users || 0, icon: faUserCheck, color: 'green' },
  { key: 'pending_approvals', label: 'Pending Approval', value: stats?.pending_approvals || 0, icon: faHourglassHalf, color: 'orange' },  // ✅ fixed
  { key: 'blocked_users', label: 'Blocked', value: stats?.blocked_users || 0, icon: faLock, color: 'red' },
  { key: 'high_risk_users', label: 'High Risk', value: stats?.high_risk_users || 0, icon: faFire, color: 'purple' },
  { key: 'failed_logins_24h', label: 'Failed Logins (24h)', value: stats?.failed_logins_24h || 0, icon: faExclamationTriangle, color: 'red' },
];

  if (loading && !stats) {
    return <div className="admin-loading">Loading Admin Panel...</div>;
  }

  if (error) {
    return (
      <div className="admin-error">
        <p>{error}</p>
        <button className="btn-primary" onClick={fetchData}>Retry</button>
      </div>
    );
  }

  return (
    <div className="admin-panel">
      <div className="admin-header">
        <div>
          <h1>🛡️ Admin Control Centre</h1>
          <p className="admin-subtitle">User management, security monitoring & audit trails</p>
        </div>
        <button className="btn-secondary" onClick={fetchData}>
          <FontAwesomeIcon icon={faSync} /> Refresh
        </button>
      </div>

      <div className="admin-stats-grid">
        {statItems.map((item) => (
          <div key={item.key} className={`stat-card ${item.color}`}>
            <div className="stat-icon">
              <FontAwesomeIcon icon={item.icon} />
            </div>
            <div className="stat-content">
              <span className="stat-value">{item.value}</span>
              <span className="stat-label">{item.label}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="admin-tabs">
        <button
          className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <FontAwesomeIcon icon={faClipboardList} /> Overview
        </button>
        <button
          className={`tab ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => setActiveTab('users')}
        >
          <FontAwesomeIcon icon={faUsers} /> Users
        </button>
        <button
          className={`tab ${activeTab === 'pending' ? 'active' : ''}`}
          onClick={() => setActiveTab('pending')}
        >
          <FontAwesomeIcon icon={faUserPlus} /> Pending
        </button>
        <button
          className={`tab ${activeTab === 'alerts' ? 'active' : ''}`}
          onClick={() => setActiveTab('alerts')}
        >
          <FontAwesomeIcon icon={faBell} /> Alerts
        </button>
        <button
          className={`tab ${activeTab === 'logs' ? 'active' : ''}`}
          onClick={() => setActiveTab('logs')}
        >
          <FontAwesomeIcon icon={faEye} /> Login Logs
        </button>
      </div>

      <div className="admin-content">
        {activeTab === 'overview' && (
          <div className="overview-grid">
            <div className="overview-card welcome">
              <h3>Welcome to the Admin Centre</h3>
              <p>Use the tabs above to manage users, review security alerts, and audit login activity across FraudGuard.</p>
            </div>
            <div className="overview-card">
              <h4><FontAwesomeIcon icon={faHourglassHalf} /> Pending Approvals</h4>
              <p>{stats?.pending_users || 0} pending registrations</p>
              <button className="btn-secondary" onClick={() => setActiveTab('pending')}>Review Now →</button>
            </div>
            <div className="overview-card">
              <h4><FontAwesomeIcon icon={faBell} /> Security Alerts</h4>
              <p>{alerts.length} active security alerts</p>
              <button className="btn-secondary" onClick={() => setActiveTab('alerts')}>View Alerts →</button>
            </div>
            <div className="overview-card">
              <h4><FontAwesomeIcon icon={faUsers} /> User Management</h4>
              <p>{stats?.total_users || 0} total users — {stats?.blocked_users || 0} blocked</p>
              <button className="btn-secondary" onClick={() => setActiveTab('users')}>Manage Users →</button>
            </div>
            <div className="overview-card">
              <h4><FontAwesomeIcon icon={faEye} /> Login Audit Logs</h4>
              <p>{stats?.failed_logins_24h || 0} failed login attempts in the last 24 hours</p>
              <button className="btn-secondary" onClick={() => setActiveTab('logs')}>View Logs →</button>
            </div>
          </div>
        )}

        {activeTab === 'users' && (
          <div className="users-section">
            <div className="user-table-wrapper">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Last Active</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.length === 0 ? (
                    <tr><td colSpan="5" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>No users found.</td></tr>
                  ) : (
                    users.map(user => {
                      const isAdmin = user.role === 'admin';
                      return (
                        <tr key={user.id}>
                          <td>{user.username}</td>
                          <td>{user.role}</td>
                          <td><StatusBadge status={user.status} /></td>
                          <td>{user.last_active ? new Date(user.last_active).toLocaleString() : 'Never'}</td>
                          <td>
                            {user.status === 'active' && !isAdmin && (
                              <button className="btn-danger" onClick={() => handleBlock(user)}>Block</button>
                            )}
                            {user.status === 'active' && isAdmin && (
                              <span className="text-muted" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>🔒 Protected</span>
                            )}
                            {user.status === 'blocked' && (
                              <>
                                <button className="btn-success" onClick={() => handleUnblock(user.id)}>Unblock</button>
                                {!isAdmin && (
                                  <button className="btn-danger" onClick={() => handleDelete(user)}>Delete</button>
                                )}
                              </>
                            )}
                            {user.status === 'pending' && (
                              <>
                                <button className="btn-success" onClick={() => handleApprove(user.id, true)}>Approve</button>
                                <button className="btn-danger" onClick={() => handleApprove(user.id, false)}>Reject</button>
                              </>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'pending' && (
          <div className="pending-section">
            {pending.length === 0 ? (
              <p>No pending registrations.</p>
            ) : (
              <table className="admin-table">
                <thead>
                  <tr><th>Username</th><th>Role</th><th>Registered</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {pending.map(user => (
                    <tr key={user.id}>
                      <td>{user.username}</td>
                      <td>{user.role}</td>
                      <td>{new Date(user.created_at).toLocaleString()}</td>
                      <td>
                        <button className="btn-success" onClick={() => handleApprove(user.id, true)}>Approve</button>
                        <button className="btn-danger" onClick={() => handleApprove(user.id, false)}>Reject</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeTab === 'alerts' && (
          <div className="alerts-section">
            {alerts.length === 0 ? (
              <p>No active security alerts.</p>
            ) : (
              <ul className="alerts-list">
                {alerts.map((alert, idx) => (
                  <li key={idx} className={`alert-item ${alert.severity}`}>
                    <div className="alert-icon">
                      <FontAwesomeIcon icon={faExclamationTriangle} />
                    </div>
                    <div className="alert-content">
                      <strong>{alert.username}</strong> – {alert.attempts} failed attempts
                      <div className="alert-detail">
                        Last: {new Date(alert.last_attempt).toLocaleString()} · IPs: {alert.ips.join(', ')}
                      </div>
                    </div>
                    <span className={`alert-severity ${alert.severity}`}>{alert.severity}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {activeTab === 'logs' && (
          <div className="logs-section">
            <table className="admin-table">
              <thead>
                <tr><th>Time</th><th>User</th><th>Success</th><th>IP</th><th>User Agent</th></tr>
              </thead>
              <tbody>
                {logs.length === 0 ? (
                  <tr><td colSpan="5" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>No logs found.</td></tr>
                ) : (
                  logs.map((log, idx) => (
                    <tr key={idx}>
                      <td>{new Date(log.timestamp).toLocaleString()}</td>
                      <td>{log.username}</td>
                      <td><StatusBadge status={log.success ? 200 : 401} label={log.success ? '✅' : '❌'} /></td>
                      <td>{log.ip}</td>
                      <td>{log.user_agent}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}