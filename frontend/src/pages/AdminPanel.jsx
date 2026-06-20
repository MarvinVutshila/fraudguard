import { useState, useEffect } from 'react';
import api from '../services/api';

export default function AdminPanel() {
  const [pendingUsers, setPendingUsers] = useState([]);
  const [loginLogs, setLoginLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchAdminData = async () => {
    try {
      const [usersRes, logsRes] = await Promise.all([
        api.get('/admin/users/pending'),
        api.get('/admin/login-logs')
      ]);

      // Safely extract pending users
      const pending = Array.isArray(usersRes.data?.pending) ? usersRes.data.pending : [];
      setPendingUsers(pending);

      // Safely extract login logs – handle various response formats
      let logs = [];
      if (logsRes.data) {
        if (Array.isArray(logsRes.data)) {
          logs = logsRes.data;
        } else if (Array.isArray(logsRes.data.logs)) {
          logs = logsRes.data.logs;
        } else if (Array.isArray(logsRes.data.results)) {
          logs = logsRes.data.results;
        } else if (Array.isArray(logsRes.data.items)) {
          logs = logsRes.data.items;
        } else {
          // If it's a single object, wrap it (but log a warning)
          console.warn('Unexpected login logs format:', logsRes.data);
          logs = [];
        }
      }
      setLoginLogs(logs);
    } catch (err) {
      console.error('Failed to fetch admin data:', err);
      // Set empty arrays on error
      setPendingUsers([]);
      setLoginLogs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdminData();
    const onRefresh = () => fetchAdminData();
    window.addEventListener('refresh', onRefresh);
    return () => window.removeEventListener('refresh', onRefresh);
  }, []);

  const handleApproval = async (userId, approve) => {
    try {
      await api.post('/admin/users/approve', { user_id: userId, approve });
      fetchAdminData();
    } catch (err) {
      alert('Action failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  if (loading) return <div className="loading">Loading admin panel…</div>;

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title" style={{color:'var(--purple)'}}>🛡️ Pending User Approvals</div>
            <div className="card-sub">New registrations awaiting admin review</div>
          </div>
          <button className="btn-secondary" onClick={fetchAdminData}>↺ Refresh</button>
        </div>
        {pendingUsers.length === 0 ? (
          <div style={{textAlign:'center', padding:'2rem', color:'var(--success)'}}>✅ No pending registrations</div>
        ) : (
          pendingUsers.map(u => (
            <div key={u.id} className="admin-user-card">
              <div className="admin-user-info">
                <img className="admin-user-avatar" src={u.avatar_url || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect fill='%23111929' width='100' height='100'/%3E%3Ctext y='.9em' x='50%25' text-anchor='middle' font-size='54'%3E👤%3C/text%3E%3C/svg%3E"} alt="avatar" />
                <div>
                  <div className="admin-user-name">{u.username}</div>
                  <div className="admin-user-meta">ID: {u.id} · <span className="status-badge pending">PENDING</span></div>
                </div>
              </div>
              <div className="admin-actions">
                <button className="btn-success" onClick={() => handleApproval(u.id, true)}>✓ Approve</button>
                <button className="btn-danger" onClick={() => handleApproval(u.id, false)}>✗ Reject</button>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">📋 Login Audit Logs</div>
            <div className="card-sub">Recent authentication attempts across all users</div>
          </div>
          <button className="btn-secondary" onClick={fetchAdminData}>↺ Refresh</button>
        </div>
        <div className="table-scroll">
          <table className="data-tbl">
            <thead><tr><th>Email / Username</th><th>Status</th><th>IP Address</th><th>User Agent</th><th>Timestamp</th></tr></thead>
            <tbody>
              {loginLogs.length === 0 ? (
                <tr><td colSpan="5" style={{textAlign:'center', padding:'1.5rem', color:'var(--text-muted)'}}>No login logs found</td></tr>
              ) : (
                loginLogs.slice(0, 100).map((log, i) => (
                  <tr key={log.id || i}>
                    <td><strong>{log.username || '—'}</strong></td>
                    <td>{log.success ? <span className="log-success">✓ Success</span> : <span className="log-fail">✗ Failed</span>}</td>
                    <td className="font-mono">{log.ip_address || log.ip || '—'}</td>
                    <td style={{fontSize:'0.7rem', color:'var(--text-muted)', maxWidth:'200px', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}} title={log.user_agent || ''}>{log.user_agent || '—'}</td>
                    <td>{log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}