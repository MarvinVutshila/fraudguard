import { useState, useEffect, useRef } from 'react';
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  DoughnutController,
  ArcElement,
  LineElement,
  PointElement,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import api from '../services/api';

ChartJS.register(
  BarElement,
  CategoryScale,
  LinearScale,
  DoughnutController,
  ArcElement,
  LineElement,
  PointElement,
  Tooltip,
  Legend,
  Filler,
);

export default function Dashboard() {
  const [transactions, setTransactions] = useState([]);
  const [totalTransactions, setTotalTransactions] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [decisionFilter, setDecisionFilter] = useState('');
  const intervalRef = useRef(null);

  const fetchData = async () => {
    console.log('[Dashboard] fetchData called');
    setLoading(true);
    try {
      const res = await api.get('/transactions?limit=200');
      console.log('[Dashboard] API response:', res.data);
      const data = res.data.transactions || [];
      const total = res.data.total || data.length;
      console.log('[Dashboard] transactions count:', data.length, 'total:', total);
      setTransactions(data);
      setTotalTransactions(total);
    } catch (err) {
      console.error('[Dashboard] API error:', err);
    } finally {
      setLoading(false);
      console.log('[Dashboard] loading set to false');
    }
  };

  useEffect(() => {
    fetchData();
    intervalRef.current = setInterval(fetchData, 30000);
    const onRefresh = () => fetchData();
    window.addEventListener('refresh', onRefresh);
    return () => {
      clearInterval(intervalRef.current);
      window.removeEventListener('refresh', onRefresh);
    };
  }, []);

  // ─── FIX: Use local time for "today" ──────────────────────────────
  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);

  const todayTxs = transactions.filter(tx => {
    const d = new Date(tx.timestamp);
    return d >= todayStart;
  });

  // ─── Everything else unchanged ──────────────────────────────────────
  const blocked = transactions.filter(tx => tx.decision === 'BLOCK').length;
  const review = transactions.filter(tx => tx.decision === 'REVIEW' && !tx.overridden).length;
  const avgRisk = transactions.length
    ? (transactions.reduce((s, tx) => s + (tx.probability || 0), 0) / transactions.length)
    : 0;

  const riskCounts = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
  transactions.forEach(tx => {
    if (tx.risk_level && riskCounts.hasOwnProperty(tx.risk_level)) {
      riskCounts[tx.risk_level]++;
    }
  });

  const decCounts = { APPROVE: 0, BLOCK: 0, REVIEW: 0 };
  transactions.forEach(tx => {
    if (tx.decision && decCounts.hasOwnProperty(tx.decision)) {
      decCounts[tx.decision]++;
    }
  });

  const filtered = transactions
    .filter(tx =>
      (!search || (tx.transaction_id || '').toLowerCase().includes(search.toLowerCase())) &&
      (!decisionFilter || tx.decision === decisionFilter)
    )
    .slice(0, 50);

  const riskChartData = {
    labels: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
    datasets: [{
      data: [riskCounts.LOW, riskCounts.MEDIUM, riskCounts.HIGH, riskCounts.CRITICAL],
      backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
      borderRadius: 4,
    }]
  };

  const decChartData = {
    labels: ['APPROVE', 'BLOCK', 'REVIEW'],
    datasets: [{
      data: [decCounts.APPROVE, decCounts.BLOCK, decCounts.REVIEW],
      backgroundColor: ['#10b981', '#ef4444', '#f59e0b'],
      borderWidth: 0,
    }]
  };

  const last30 = transactions.slice(0, 30).reverse();
  const trendData = {
    labels: last30.map((_, i) => i + 1),
    datasets: [{
      label: 'Fraud Probability',
      data: last30.map(tx => tx.probability || 0),
      borderColor: '#ef4444',
      backgroundColor: 'rgba(239,68,68,0.05)',
      fill: true,
      tension: 0.3,
      pointRadius: 1,
    }]
  };

  return (
    <div className="dashboard">
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-icon blue">💰</div>
          <div>
            <div className="kpi-label">Today's Transactions</div>
            <div className="kpi-value">{todayTxs.length}</div>
            <div className="kpi-delta">of {totalTransactions} total</div>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon red">🚫</div>
          <div>
            <div className="kpi-label">Blocked</div>
            <div className="kpi-value">{blocked}</div>
            <div className="kpi-delta">{totalTransactions ? ((blocked/totalTransactions)*100).toFixed(1) : 0}% fraud rate</div>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon yellow">⚠️</div>
          <div>
            <div className="kpi-label">Pending Review</div>
            <div className="kpi-value">{review}</div>
            <div className="kpi-delta">awaiting human decision</div>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon green">📊</div>
          <div>
            <div className="kpi-label">Avg Risk Score</div>
            <div className="kpi-value">{avgRisk.toFixed(4)}</div>
            <div className="kpi-delta">mean fraud probability</div>
          </div>
        </div>
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <div className="chart-header">
            <span className="chart-title">Risk Distribution</span>
          </div>
          <div className="chart-container">
            <Bar data={riskChartData} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }} />
          </div>
        </div>
        <div className="chart-card">
          <div className="chart-header">
            <span className="chart-title">Decision Split</span>
          </div>
          <div className="chart-container doughnut">
            <Doughnut data={decChartData} options={{ cutout: '65%', plugins: { legend: { display: false } } }} />
          </div>
          <div className="doughnut-legend">
            <div><span className="dot" style={{background:'#10b981'}}></span> Approve: {decCounts.APPROVE}</div>
            <div><span className="dot" style={{background:'#ef4444'}}></span> Block: {decCounts.BLOCK}</div>
            <div><span className="dot" style={{background:'#f59e0b'}}></span> Review: {decCounts.REVIEW}</div>
          </div>
        </div>
        <div className="chart-card">
          <div className="chart-header">
            <span className="chart-title">Probability Trend</span>
            <span className="chart-sub">Last 30 transactions</span>
          </div>
          <div className="chart-container">
            <Line data={trendData} options={{ responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, max: 1 } }, plugins: { legend: { display: false } } }} />
          </div>
        </div>
      </div>

      <div className="transaction-table">
        <div className="table-header">
          <div className="table-title">
            <span>📡 Live Transactions</span>
            <span className="table-sub">Auto‑refreshes every 30s</span>
          </div>
          <div className="table-controls">
            <input
              type="text"
              placeholder="Search by ID…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select
              value={decisionFilter}
              onChange={(e) => setDecisionFilter(e.target.value)}
            >
              <option value="">All Decisions</option>
              <option value="APPROVE">Approve</option>
              <option value="REVIEW">Review</option>
              <option value="BLOCK">Block</option>
            </select>
            <button className="btn-secondary" onClick={fetchData}>↺ Refresh</button>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Transaction ID</th>
                <th>Amount</th>
                <th>Probability</th>
                <th>Decision</th>
                <th>Risk Level</th>
                <th>Effective</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="7" className="loading">Loading…</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan="7" className="empty">No transactions match.</td></tr>
              ) : (
                filtered.map((tx, index) => {
                  const id = tx.transaction_id || tx.id || `tx-${index}`;
                  const effective = tx.overridden ? tx.effective_decision : tx.decision;
                  return (
                    <tr key={tx.id || `${tx.transaction_id}-${index}`} className={tx.risk_level === 'CRITICAL' ? 'critical' : ''}>
                      <td className="font-mono">{id}</td>
                      <td><strong>${(tx.amount || 0).toFixed(2)}</strong></td>
                      <td className="font-mono">{(tx.probability || 0).toFixed(4)}</td>
                      <td><span className={`badge decision ${tx.decision}`}>{tx.decision}</span></td>
                      <td><span className={`badge risk ${(tx.risk_level || '').toLowerCase()}`}>{tx.risk_level || '—'}</span></td>
                      <td>
                        {tx.overridden ? (
                          <span className="badge decision overridden">{effective} <span className="note">(overridden)</span></span>
                        ) : (
                          <span className={`badge decision ${tx.decision}`}>{tx.decision}</span>
                        )}
                      </td>
                      <td>
                        {tx.decision === 'REVIEW' && !tx.overridden ? (
                          <button className="btn-override" onClick={() => alert(`Override ${id}`)}>⚖ Override</button>
                        ) : tx.overridden ? (
                          <span className="text-muted text-sm">by {tx.overridden_by || 'analyst'}</span>
                        ) : null}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
