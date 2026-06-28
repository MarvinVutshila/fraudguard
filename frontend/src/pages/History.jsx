import { useState, useEffect } from 'react';
import api from '../services/api';

export default function History() {
  const [transactions, setTransactions] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [filtered, setFiltered] = useState([]);
  const [search, setSearch] = useState('');
  const [decisionFilter, setDecisionFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 25;

  // Badge counts – starts with 0, then filled from summary or local fallback
  const [badges, setBadges] = useState({
    blocked: 0,
    review: 0,
    overridden: 0,
  });

  // Fetch the transaction list (with filters)
  const fetchHistory = async () => {
    try {
      const params = new URLSearchParams();
      params.set('limit', '1500');
      if (search) params.set('search', search);
      if (decisionFilter) params.set('decision', decisionFilter);
      if (riskFilter) params.set('risk_level', riskFilter);

      const res = await api.get(`/transactions?${params}`);
      const data = res.data.transactions || [];
      const total = res.data.total || data.length;

      setTransactions(data);
      setTotalCount(total);
      setFiltered(data);
    } catch (err) {
      console.error('Failed to fetch history:', err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch aggregated summary counts (optional endpoint)
  const fetchSummary = async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      if (decisionFilter) params.set('decision', decisionFilter);
      if (riskFilter) params.set('risk_level', riskFilter);

      const res = await api.get(`/transactions/summary?${params}`);
      setBadges({
        blocked: res.data.blocked || 0,
        review: res.data.review || 0,
        overridden: res.data.overridden || 0,
      });
    } catch (err) {
      // Fallback: count from the currently loaded records
      console.warn('Summary endpoint not available – using local counts.');
      setBadges({
        blocked: filtered.filter(t => t.decision === 'BLOCK').length,
        review: filtered.filter(t => t.decision === 'REVIEW').length,
        overridden: filtered.filter(t => t.overridden).length,
      });
    }
  };

  // Fetch both list and summary on mount & filter changes
  useEffect(() => {
    fetchHistory();
  }, [search, decisionFilter, riskFilter]);

  useEffect(() => {
    fetchSummary();
  }, [search, decisionFilter, riskFilter, filtered]);

  // Initial load + refresh listener
  useEffect(() => {
    fetchHistory();
    fetchSummary();
    const onRefresh = () => {
      fetchHistory();
      fetchSummary();
    };
    window.addEventListener('refresh', onRefresh);
    return () => window.removeEventListener('refresh', onRefresh);
  }, []);

  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);
  const totalPages = Math.ceil(filtered.length / pageSize);

  const getPageNumbers = (currentPage, totalPages, maxVisible = 5) => {
    if (totalPages <= maxVisible + 2) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    const pages = [];
    pages.push(1);
    let start = Math.max(2, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages - 1, currentPage + Math.floor(maxVisible / 2));
    if (currentPage - 2 < Math.floor(maxVisible / 2)) {
      end = Math.min(totalPages - 1, 1 + maxVisible);
    }
    if (totalPages - currentPage <= Math.floor(maxVisible / 2)) {
      start = Math.max(2, totalPages - maxVisible);
    }
    if (start > 2) pages.push('...');
    for (let i = start; i <= end; i++) pages.push(i);
    if (end < totalPages - 1) pages.push('...');
    pages.push(totalPages);
    return pages;
  };

  const exportCSV = () => {
    const headers = [
      'transaction_id', 'amount', 'probability', 'decision',
      'risk_level', 'effective_decision', 'overridden_by', 'timestamp'
    ];
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
            <input
              type="text"
              placeholder="Search by ID…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
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
            <button className="btn-secondary" onClick={() => { fetchHistory(); fetchSummary(); }}>
              ↺ Refresh
            </button>
            <button className="btn-primary" onClick={exportCSV}>
              ⬇ Export CSV
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <span className="risk-badge low">Total: {totalCount}</span>
          <span className="risk-badge high">Blocked: {badges.blocked}</span>
          <span className="risk-badge medium">Review: {badges.review}</span>
          <span className="risk-badge critical">Overridden: {badges.overridden}</span>
        </div>

        <div className="table-scroll">
          <table className="data-tbl">
            <thead>
              <tr>
                <th>Transaction ID</th>
                <th>Amount</th>
                <th>Probability</th>
                <th>Decision</th>
                <th>Risk Level</th>
                <th>Effective</th>
                <th>Overridden By</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {paginated.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '2rem' }}>
                    No transactions match.
                  </td>
                </tr>
              ) : (
                paginated.map((tx, index) => {
                  const effective = tx.overridden ? tx.effective_decision : tx.decision;
                  return (
                    <tr
                      key={tx.id || `${tx.transaction_id}-${index}`}
                      className={tx.risk_level === 'CRITICAL' ? 'critical' : ''}
                    >
                      <td className="font-mono">{tx.transaction_id || 'N/A'}</td>
                      <td>${(tx.amount || 0).toFixed(2)}</td>
                      <td>{((tx.probability || 0) * 100).toFixed(1)}%</td>
                      <td>
                        <span className={`badge decision ${tx.decision}`}>
                          {tx.decision}
                        </span>
                      </td>
                      <td>
                        <span className={`badge risk ${(tx.risk_level || '').toLowerCase()}`}>
                          {tx.risk_level || '—'}
                        </span>
                      </td>
                      <td>
                        <span className={`badge decision ${effective}`}>
                          {effective}
                        </span>
                      </td>
                      <td>{tx.overridden_by || '—'}</td>
                      <td>
                        {tx.timestamp ? new Date(tx.timestamp).toLocaleString() : '—'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '0.25rem',
              marginTop: '1rem',
              alignItems: 'center',
            }}
          >
            <button
              className="btn-secondary"
              disabled={page === 1}
              onClick={() => setPage(p => p - 1)}
            >
              ‹
            </button>

            {getPageNumbers(page, totalPages).map((p, idx) =>
              p === '...' ? (
                <span key={`ellipsis-${idx}`} style={{ padding: '0.25rem 0.5rem' }}>
                  …
                </span>
              ) : (
                <button
                  key={p}
                  className={p === page ? 'btn-primary' : 'btn-secondary'}
                  onClick={() => setPage(p)}
                >
                  {p}
                </button>
              )
            )}

            <button
              className="btn-secondary"
              disabled={page === totalPages}
              onClick={() => setPage(p => p + 1)}
            >
              ›
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
