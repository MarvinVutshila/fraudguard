import { useState, useEffect } from 'react';
import api from '../services/api';

export default function History() {
  const [transactions, setTransactions] = useState([]);
  const [totalCount, setTotalCount] = useState(0);  // <-- NEW: store the true total
  const [filtered, setFiltered] = useState([]);
  const [search, setSearch] = useState('');
  const [decisionFilter, setDecisionFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const fetchHistory = async () => {
    try {
      const res = await api.get('/transactions?limit=1500');
      const data = res.data.transactions || [];
      const total = res.data.total || data.length;  // <-- get total from API
      setTransactions(data);
      setTotalCount(total);  // <-- store it
      applyFilters(data);
    } catch (err) {
      console.error('Failed to fetch history:', err);
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = (data = transactions) => {
    let result = data;
    if (search) {
      result = result.filter(tx => (tx.transaction_id || '').toLowerCase().includes(search.toLowerCase()));
    }
    if (decisionFilter) {
      result = result.filter(tx => tx.decision === decisionFilter);
    }
    if (riskFilter) {
      result = result.filter(tx => tx.risk_level === riskFilter);
    }
    setFiltered(result);
    setPage(1);
  };

  useEffect(() => {
    fetchHistory();
    const onRefresh = () => fetchHistory();
    window.addEventListener('refresh', onRefresh);
    return () => window.removeEventListener('refresh', onRefresh);
  }, []);

  useEffect(() => {
    applyFilters();
  }, [search, decisionFilter, riskFilter, transactions]);

  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);
  const totalPages = Math.ceil(filtered.length / pageSize);

  const exportCSV = () => {
    const headers = ['transaction_id', 'amount', 'probability', 'decision', 'risk_level', 'effective_decision', 'overridden_by', 'timestamp'];
    const rows = filtered.map(tx => [
      tx.transaction_id || '',
      tx.amount || 0,
      tx.probability || 0,
      tx.decision,
      tx.risk_level || '',
      tx.overridden ? tx.effective_decision : tx.decision,
      tx.overridden_by || '',
      tx.timestamp || ''
    ]);
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `history_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
  };

  if (loading) return <div className="loading">Loading history…</div>;

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">📋 Transaction History</div>
            <div className="card-sub">Full audit trail with override history</div>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <input type="text" placeholder="Search by ID…" value={search} onChange={e => setSearch(e.target.value)} />
            <select value={decisionFilter} onChange={e => setDecisionFilter(e.target.value)}>
              <option value="">All Decisions</option>
              <option value="APPROVE">Approve</option>
              <option value="REVIEW">Review</option>
              <option value="BLOCK">Block</option>
            </select>
            <select value={riskFilter} onChange={e => setRiskFilter(e.target.value)}>
              <option value="">All Risk</option>
              <option value="LOW">Low</option>
              <option value="MEDIUM">Medium</option>
              <option value="HIGH">High</option>
              <option value="CRITICAL">Critical</option>
            </select>
            <button className="btn-secondary" onClick={fetchHistory}>↺ Refresh</button>
            <button className="btn-primary" onClick={exportCSV}>⬇ Export CSV</button>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <span className="risk-badge low">Total: {totalCount}</span> {/* <-- CHANGED: use totalCount */}
          <span className="risk-badge high">Blocked: {filtered.filter(t => t.decision === 'BLOCK').length}</span>
          <span className="risk-badge medium">Review: {filtered.filter(t => t.decision === 'REVIEW').length}</span>
          <span className="risk-badge critical">Overridden: {filtered.filter(t => t.overridden).length}</span>
        </div>
        <div className="table-scroll">
          <table className="data-tbl">
            <thead><tr><th>Transaction ID</th><th>Amount</th><th>Probability</th><th>Decision</th><th>Risk Level</th><th>Effective</th><th>Overridden By</th><th>Timestamp</th></tr></thead>
            <tbody>
              {paginated.length === 0 ? (
                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '2rem' }}>No transactions match.</td></tr>
              ) : (
                paginated.map((tx, index) => {
                  const effective = tx.overridden ? tx.effective_decision : tx.decision;
                  return (
                    <tr key={tx.id || `${tx.transaction_id}-${index}`} className={tx.risk_level === 'CRITICAL' ? 'critical' : ''}>
                      <td className="font-mono">{tx.transaction_id || 'N/A'}</td>
                      <td>${(tx.amount || 0).toFixed(2)}</td>
                      <td>{((tx.probability || 0) * 100).toFixed(1)}%</td>
                      <td><span className={`badge decision ${tx.decision}`}>{tx.decision}</span></td>
                      <td><span className={`badge risk ${(tx.risk_level || '').toLowerCase()}`}>{tx.risk_level || '—'}</span></td>
                      <td><span className={`badge decision ${effective}`}>{effective}</span></td>
                      <td>{tx.overridden_by || '—'}</td>
                      <td>{tx.timestamp ? new Date(tx.timestamp).toLocaleString() : '—'}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.25rem', marginTop: '1rem' }}>
            <button className="btn-secondary" disabled={page === 1} onClick={() => setPage(p => p - 1)}>‹</button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
              <button key={p} className={p === page ? 'btn-primary' : 'btn-secondary'} onClick={() => setPage(p)}>{p}</button>
            ))}
            <button className="btn-secondary" disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>›</button>
          </div>
        )}
      </div>
    </div>
  );
}
