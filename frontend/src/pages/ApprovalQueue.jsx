import { useState, useEffect } from 'react';
import api from '../services/api';

export default function ApprovalQueue() {
  const [pendingReviews, setPendingReviews] = useState([]);
  const [auditLog, setAuditLog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [selectedTx, setSelectedTx] = useState(null);
  const [newDecision, setNewDecision] = useState('APPROVE');
  const [reason, setReason] = useState('');
  const [userRole, setUserRole] = useState('analyst');

  // Get user role from token
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

  const fetchData = async () => {
    try {
      // ✅ FIX: Fetch pending reviews from the public endpoint (accessible to all)
      const pendingRes = await api.get('/transactions?decision=REVIEW&limit=100');
      setPendingReviews(pendingRes.data.transactions || []);

      // ✅ FIX: For audit log, try to fetch from public endpoint first
      // If user is admin, they can see all overrides; if analyst, they see their own
      const isAdmin = getUserRole() === 'admin';
      
      // Try to fetch audit log from a public endpoint
      // If the admin endpoint fails (403), just show a message
      try {
        const auditRes = await api.get('/admin/overrides');
        const logs = Array.isArray(auditRes.data) ? auditRes.data : (auditRes.data.overrides || []);
        setAuditLog(logs);
      } catch (err) {
        if (err.response?.status === 403) {
          // Analyst doesn't have access to full audit log - show limited view
          // Or we could show an empty state with a message
          setAuditLog([]);
          console.log('Audit log view restricted to admins');
        } else {
          throw err;
        }
      }
    } catch (err) {
      console.error('Failed to fetch approval data:', err);
      // Show error message to user
      alert('Failed to load approval queue: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const role = getUserRole();
    setUserRole(role);
    fetchData();
    const onRefresh = () => fetchData();
    window.addEventListener('refresh', onRefresh);
    return () => window.removeEventListener('refresh', onRefresh);
  }, []);

  // ✅ FIX: Bulk approve - now uses the public endpoint (accessible to all)
  const handleApproveAll = async () => {
    if (pendingReviews.length === 0) return;
    if (!window.confirm('Approve all pending reviews?')) return;

    try {
      // ✅ Use the public override endpoint for each transaction
      for (const tx of pendingReviews) {
        await api.post(`/transactions/${tx.transaction_id || tx.id}/override`, {
          new_decision: 'APPROVE',
          reason: 'Bulk approved via Approve All'
        });
      }
      fetchData();
    } catch (err) {
      alert('Failed to approve all: ' + (err.response?.data?.detail || err.message));
    }
  };

  const openOverrideModal = (tx) => {
    setSelectedTx(tx);
    setNewDecision(tx.decision === 'REVIEW' ? 'APPROVE' : 'APPROVE');
    setReason('');
    setShowModal(true);
  };

  // ✅ FIX: Override now uses public endpoint (accessible to all)
  const handleOverride = async () => {
    if (!selectedTx) return;
    try {
      await api.post(`/transactions/${selectedTx.transaction_id || selectedTx.id}/override`, {
        new_decision: newDecision,
        reason: reason.trim() || 'No reason provided'
      });
      setShowModal(false);
      setSelectedTx(null);
      fetchData();
    } catch (err) {
      alert('Override failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  const exportCSV = () => {
    if (auditLog.length === 0) {
      alert('No audit log entries to export.');
      return;
    }

    const headers = ['ID', 'Amount', 'Probability', 'Model', 'Human Decision', 'Analyst', 'Reason', 'Time'];
    const rows = auditLog.map(log => [
      log.transaction_id || log.id || '—',
      log.amount || 0,
      log.probability ? `${(log.probability * 100).toFixed(1)}%` : '—',
      log.model || log.original_decision || '—',
      log.human_decision || log.new_decision || '—',
      log.overridden_by || log.analyst || '—',
      log.reason || '—',
      log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'
    ]);

    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `approval_audit_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) return <div className="loading">Loading approval data…</div>;

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">⚖️ Human Approval Queue</div>
            <div className="card-sub">Transactions flagged as REVIEW — requires analyst decision</div>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn-secondary" onClick={fetchData}>↺ Refresh</button>
            <button
              className="btn-primary"
              onClick={handleApproveAll}
              disabled={pendingReviews.length === 0}
            >
              ✓ Approve All
            </button>
          </div>
        </div>
        {pendingReviews.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--success)' }}>
            ✅ No pending reviews
          </div>
        ) : (
          <div className="table-scroll">
            <table className="data-tbl">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Amount</th>
                  <th>Probability</th>
                  <th>Decision</th>
                  <th>Risk Level</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {pendingReviews.map(tx => (
                  <tr key={tx.transaction_id || tx.id}>
                    <td className="font-mono">{tx.transaction_id || tx.id}</td>
                    <td>${(tx.amount || 0).toFixed(2)}</td>
                    <td>{((tx.probability || 0) * 100).toFixed(1)}%</td>
                    <td><span className="badge decision REVIEW">REVIEW</span></td>
                    <td><span className={`badge risk ${(tx.risk_level || '').toLowerCase()}`}>{tx.risk_level || '—'}</span></td>
                    <td>
                      <button className="btn-secondary" onClick={() => openOverrideModal(tx)}>
                        ⚖ Override
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">📝 Approval Audit Log</div>
            <div className="card-sub">
              {userRole === 'admin' 
                ? 'History of all human decisions' 
                : 'Your recent decisions (admin view shows all)'}
            </div>
          </div>
          <button className="btn-primary" onClick={exportCSV} disabled={auditLog.length === 0}>
            ⬇ Export
          </button>
        </div>
        <div className="table-scroll">
          <table className="data-tbl">
            <thead>
              <tr>
                <th>ID</th>
                <th>Amount</th>
                <th>Probability</th>
                <th>Model</th>
                <th>Human Decision</th>
                <th>Analyst</th>
                <th>Reason</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {auditLog.length === 0 ? (
                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
                  {userRole === 'admin' 
                    ? 'No decisions recorded yet' 
                    : 'Admin-only view. Your decisions are recorded in the system.'}
                </td></tr>
              ) : (
                auditLog.slice(0, 100).map((log, idx) => (
                  <tr key={log.id || idx}>
                    <td className="font-mono">{log.transaction_id || log.id || '—'}</td>
                    <td>${(log.amount || 0).toFixed(2)}</td>
                    <td>{log.probability ? `${(log.probability * 100).toFixed(1)}%` : '—'}</td>
                    <td>{log.model || log.original_decision || '—'}</td>
                    <td><span className={`badge decision ${log.human_decision || log.new_decision}`}>
                      {log.human_decision || log.new_decision || '—'}
                    </span></td>
                    <td>{log.overridden_by || log.analyst || '—'}</td>
                    <td>{log.reason || '—'}</td>
                    <td>{log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Override Modal */}
      {showModal && selectedTx && (
        <div className="modal-overlay open" onClick={() => setShowModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-hdr">
              <h3>Override Transaction</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p><strong>ID:</strong> {selectedTx.transaction_id || selectedTx.id}</p>
              <p><strong>Amount:</strong> ${(selectedTx.amount || 0).toFixed(2)}</p>
              <p><strong>Current Decision:</strong> <span className={`badge decision ${selectedTx.decision}`}>{selectedTx.decision}</span></p>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.2rem' }}>New Decision</label>
                <select value={newDecision} onChange={(e) => setNewDecision(e.target.value)}>
                  <option value="APPROVE">Approve</option>
                  <option value="BLOCK">Block</option>
                  <option value="REVIEW">Review (keep)</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.2rem' }}>Reason (optional)</label>
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Why are you overriding this decision?"
                  rows="3"
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '8px', border: '1px solid var(--border)' }}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleOverride}>Confirm Override</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
