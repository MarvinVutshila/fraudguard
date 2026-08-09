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
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  FiDollarSign, FiXCircle, FiAlertTriangle, FiBarChart2,
  FiCpu, FiHardDrive, FiDatabase, FiActivity, FiCheckCircle,
  FiClock, FiUsers, FiShield, FiTrendingUp, FiTrendingDown,
  FiRefreshCw, FiSearch, FiMoreVertical, FiGlobe
} from 'react-icons/fi';
import api from '../services/api';
import { useTheme } from '../context/ThemeContext';
import { formatDistanceToNow, format } from 'date-fns';

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
  const { isDarkMode } = useTheme();
  const [transactions, setTransactions] = useState([]);
  const [totalTransactions, setTotalTransactions] = useState(0);
  const [monitoring, setMonitoring] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [decisionFilter, setDecisionFilter] = useState('');
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const intervalRef = useRef(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [txRes, monitorRes, modelRes] = await Promise.all([
        api.get('/transactions?limit=200'),
        api.get('/monitoring/stats').catch(() => ({ data: null })),
        api.get('/model/info').catch(() => ({ data: null })),
      ]);

      const data = txRes.data.transactions || [];
      const total = txRes.data.total || data.length;
      setTransactions(data);
      setTotalTransactions(total);
      setMonitoring(monitorRes.data);
      setModelInfo(modelRes.data);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('[Dashboard] Error fetching data:', err);
    } finally {
      setLoading(false);
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

  // ─── Compute metrics ──────────────────────────────────────────────
  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);
  const todayTxs = transactions.filter(tx => new Date(tx.timestamp) >= todayStart);

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

  // ─── Theme-aware chart colours ─────────────────────────────────────
  const getChartColors = () => ({
    gridColor: isDarkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)',
    textColor: isDarkMode ? '#7a8ba5' : '#6c757d',
  });
  const chartColors = getChartColors();

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
      backgroundColor: isDarkMode ? 'rgba(239,68,68,0.1)' : 'rgba(239,68,68,0.05)',
      fill: true,
      tension: 0.3,
      pointRadius: 1,
      pointBackgroundColor: '#ef4444',
      borderWidth: 2,
    }]
  };

  const barOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: chartColors.gridColor, drawBorder: false }, ticks: { color: chartColors.textColor } },
      y: { grid: { color: chartColors.gridColor, drawBorder: false }, ticks: { color: chartColors.textColor } }
    }
  };

  const doughnutOptions = {
    cutout: '65%',
    plugins: { legend: { display: false } }
  };

  const lineOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { grid: { color: chartColors.gridColor, drawBorder: false }, ticks: { color: chartColors.textColor, maxTicksLimit: 10 } },
      y: { min: 0, max: 1, grid: { color: chartColors.gridColor, drawBorder: false }, ticks: { color: chartColors.textColor } }
    },
    plugins: { legend: { display: false } }
  };

  // ─── System Health (from monitoring) ──────────────────────────────
  const health = monitoring?.system_health || { cpu_percent: 0, memory_used_mb: 0, memory_total_mb: 0, db_connections: 0 };
  const memoryPercent = health.memory_total_mb > 0 ? (health.memory_used_mb / health.memory_total_mb * 100) : 0;
  const errorRate = monitoring?.error_rate || 0;
  const avgLatency = monitoring?.avg_latency || 0;

  return (
    <div className="dashboard" style={{ maxWidth: '1400px', margin: '0 auto', padding: '0 0.5rem' }}>

      {/* ─── Header ────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem'
      }}>
        <div>
          <h1 style={{ fontSize: 'clamp(1.1rem, 3vw, 1.4rem)', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FiShield size={22} style={{ color: 'var(--accent)' }} /> Live Feed
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 'clamp(0.7rem, 1.5vw, 0.85rem)', marginTop: '2px' }}>
            Updated {formatDistanceToNow(lastUpdated)} ago · {totalTransactions} total transactions
          </p>
        </div>
        <button className="btn-secondary" onClick={fetchData} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}>
          <FontAwesomeIcon icon={FiRefreshCw} className={loading ? 'spinning' : ''} /> Refresh
        </button>
      </div>

      {/* ─── System Health Bar ──────────────────────────────────────── */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
        gap: '0.6rem', marginBottom: '1rem'
      }}>
        {[
          { label: 'Status', value: errorRate < 5 && avgLatency < 200 ? 'Operational' : 'Degraded', icon: FiCheckCircle, color: errorRate < 5 ? '#10b981' : '#f59e0b' },
          { label: 'Latency', value: `${avgLatency.toFixed(1)}ms`, icon: FiActivity, color: '#3b82f6' },
          { label: 'Errors', value: `${errorRate.toFixed(1)}%`, icon: FiAlertTriangle, color: errorRate < 5 ? '#10b981' : '#ef4444' },
          { label: 'CPU', value: `${health.cpu_percent.toFixed(0)}%`, icon: FiCpu, color: health.cpu_percent < 70 ? '#10b981' : '#ef4444' },
          { label: 'Memory', value: `${memoryPercent.toFixed(0)}%`, icon: FiHardDrive, color: memoryPercent < 80 ? '#10b981' : '#ef4444' },
          { label: 'DB', value: health.db_connections, icon: FiDatabase, color: '#8b5cf6' },
        ].map((item) => (
          <div key={item.label} style={{
            background: 'var(--surface)',
            border: `1px solid ${item.color}33`,
            borderRadius: '8px', padding: '0.5rem 0.7rem',
            display: 'flex', alignItems: 'center', gap: '0.5rem'
          }}>
            <div style={{ color: item.color, fontSize: '1rem' }}><FontAwesomeIcon icon={item.icon} /></div>
            <div>
              <div style={{ fontSize: '0.55rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{item.label}</div>
              <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{item.value}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ─── KPI Cards ──────────────────────────────────────────────── */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
        gap: '0.8rem', marginBottom: '1rem'
      }}>
        {[
          { label: "Today's Txs", value: todayTxs.length, sub: `of ${totalTransactions} total`, icon: FiDollarSign, color: '#3b82f6' },
          { label: 'Blocked', value: blocked, sub: totalTransactions ? `${((blocked/totalTransactions)*100).toFixed(1)}%` : '0%', icon: FiXCircle, color: '#ef4444' },
          { label: 'Pending Review', value: review, sub: 'awaiting', icon: FiAlertTriangle, color: '#f59e0b' },
          { label: 'Avg Risk', value: avgRisk.toFixed(4), sub: 'mean prob', icon: FiBarChart2, color: '#8b5cf6' },
        ].map((k) => (
          <div key={k.label} style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: '10px', padding: '0.8rem 1rem',
            display: 'flex', alignItems: 'center', gap: '0.8rem'
          }}>
            <div style={{ color: k.color, fontSize: '1.4rem' }}><FontAwesomeIcon icon={k.icon} /></div>
            <div>
              <div style={{ fontSize: 'clamp(1.2rem, 2.5vw, 1.8rem)', fontWeight: 700, lineHeight: 1.2 }}>{k.value}</div>
              <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{k.label}</div>
              <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>{k.sub}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ─── Charts ──────────────────────────────────────────────────── */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '0.8rem', marginBottom: '1rem'
      }}>
        <div className="chart-card" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '10px', padding: '0.8rem' }}>
          <div className="chart-header" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
            <span className="chart-title" style={{ fontWeight: 600, fontSize: '0.75rem' }}>Risk Distribution</span>
          </div>
          <div className="chart-container" style={{ height: '120px' }}>
            <Bar data={riskChartData} options={barOptions} />
          </div>
        </div>
        <div className="chart-card" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '10px', padding: '0.8rem' }}>
          <div className="chart-header" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
            <span className="chart-title" style={{ fontWeight: 600, fontSize: '0.75rem' }}>Decision Split</span>
          </div>
          <div className="chart-container doughnut" style={{ height: '110px' }}>
            <Doughnut data={decChartData} options={doughnutOptions} />
          </div>
          <div className="doughnut-legend" style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', marginTop: '0.2rem', fontSize: '0.6rem' }}>
            <div><span className="dot" style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: '#10b981', marginRight: '3px' }}></span> {decCounts.APPROVE}</div>
            <div><span className="dot" style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: '#ef4444', marginRight: '3px' }}></span> {decCounts.BLOCK}</div>
            <div><span className="dot" style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: '#f59e0b', marginRight: '3px' }}></span> {decCounts.REVIEW}</div>
          </div>
        </div>
        <div className="chart-card" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '10px', padding: '0.8rem' }}>
          <div className="chart-header" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
            <span className="chart-title" style={{ fontWeight: 600, fontSize: '0.75rem' }}>Probability Trend</span>
            <span className="chart-sub" style={{ fontSize: '0.55rem', color: 'var(--text-muted)' }}>Last 30</span>
          </div>
          <div className="chart-container" style={{ height: '120px' }}>
            <Line data={trendData} options={lineOptions} />
          </div>
        </div>
      </div>

      {/* ─── Model Info Mini ─────────────────────────────────────────── */}
      {modelInfo && (
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: '10px', padding: '0.5rem 1rem',
          marginBottom: '1rem',
          display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '1rem'
        }}>
          <span style={{ fontWeight: 600, fontSize: '0.7rem', color: 'var(--text-muted)' }}>🤖 Model</span>
          {[
            ['Accuracy', `${(modelInfo.metrics?.accuracy || 0) * 100}%`],
            ['F1', `${(modelInfo.metrics?.f1_score || 0) * 100}%`],
            ['Threshold', modelInfo.optimal_threshold?.toFixed(3) || '0.5'],
            ['Features', modelInfo.n_features || '—'],
          ].map(([k, v]) => (
            <div key={k} style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
              <span style={{ fontSize: '0.55rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{k}</span>
              <span style={{ fontWeight: 700, fontSize: '0.75rem', fontFamily: 'var(--mono)' }}>{v}</span>
            </div>
          ))}
        </div>
      )}

      {/* ─── Transaction Table ───────────────────────────────────────── */}
      <div className="transaction-table" style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: '10px', padding: '0.8rem'
      }}>
        <div className="table-header" style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.3rem', marginBottom: '0.5rem' }}>
          <div className="table-title" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <span style={{ fontWeight: 700, fontSize: '0.8rem' }}>📡 Live Transactions</span>
            <span className="table-sub" style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>Auto‑refreshes</span>
          </div>
          <div className="table-controls" style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Search ID…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="theme-input"
              style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '4px', padding: '0.2rem 0.4rem', fontSize: '0.7rem', color: 'var(--text)', width: '100px' }}
            />
            <select
              value={decisionFilter}
              onChange={(e) => setDecisionFilter(e.target.value)}
              className="theme-select"
              style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '4px', padding: '0.2rem 0.4rem', fontSize: '0.7rem', color: 'var(--text)' }}
            >
              <option value="">All</option>
              <option value="APPROVE">Approve</option>
              <option value="REVIEW">Review</option>
              <option value="BLOCK">Block</option>
            </select>
            <button className="btn-secondary" onClick={fetchData} style={{ padding: '0.2rem 0.5rem', fontSize: '0.7rem' }}>↺</button>
          </div>
        </div>
        <div className="table-scroll" style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.65rem' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border)' }}>
                <th style={{ textAlign: 'left', padding: '0.3rem 0.3rem', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.55rem', textTransform: 'uppercase' }}>ID</th>
                <th style={{ textAlign: 'left', padding: '0.3rem 0.3rem', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.55rem', textTransform: 'uppercase' }}>Amount</th>
                <th style={{ textAlign: 'left', padding: '0.3rem 0.3rem', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.55rem', textTransform: 'uppercase' }}>Prob</th>
                <th style={{ textAlign: 'left', padding: '0.3rem 0.3rem', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.55rem', textTransform: 'uppercase' }}>Decision</th>
                <th style={{ textAlign: 'left', padding: '0.3rem 0.3rem', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.55rem', textTransform: 'uppercase' }}>Risk</th>
                <th style={{ textAlign: 'left', padding: '0.3rem 0.3rem', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.55rem', textTransform: 'uppercase' }}>Effective</th>
                <th style={{ textAlign: 'left', padding: '0.3rem 0.3rem', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.55rem', textTransform: 'uppercase' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="7" className="loading" style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-muted)' }}>Loading…</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan="7" className="empty" style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-muted)' }}>No transactions.</td></tr>
              ) : (
                filtered.map((tx, index) => {
                  const id = tx.transaction_id || tx.id || `tx-${index}`;
                  const effective = tx.overridden ? tx.effective_decision : tx.decision;
                  return (
                    <tr key={tx.id || `${tx.transaction_id}-${index}`} className={tx.risk_level === 'CRITICAL' ? 'critical' : ''} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td className="font-mono" style={{ fontFamily: 'var(--mono)', fontSize: '0.6rem', padding: '0.3rem' }}>{id}</td>
                      <td style={{ fontWeight: 600, padding: '0.3rem' }}>${(tx.amount || 0).toFixed(2)}</td>
                      <td className="font-mono" style={{ fontFamily: 'var(--mono)', fontSize: '0.6rem', padding: '0.3rem' }}>{(tx.probability || 0).toFixed(3)}</td>
                      <td style={{ padding: '0.3rem' }}><span className={`badge decision ${tx.decision}`} style={{ padding: '0.1rem 0.3rem', borderRadius: '12px', fontSize: '0.5rem', fontWeight: 600 }}>{tx.decision}</span></td>
                      <td style={{ padding: '0.3rem' }}><span className={`badge risk ${(tx.risk_level || '').toLowerCase()}`} style={{ padding: '0.1rem 0.3rem', borderRadius: '12px', fontSize: '0.5rem', fontWeight: 600 }}>{tx.risk_level || '—'}</span></td>
                      <td style={{ padding: '0.3rem' }}>
                        {tx.overridden ? (
                          <span className="badge decision overridden" style={{ padding: '0.1rem 0.3rem', borderRadius: '12px', fontSize: '0.5rem', fontWeight: 600, background: 'rgba(59,130,246,0.12)', color: '#3b82f6' }}>{effective}</span>
                        ) : (
                          <span className={`badge decision ${tx.decision}`} style={{ padding: '0.1rem 0.3rem', borderRadius: '12px', fontSize: '0.5rem', fontWeight: 600 }}>{tx.decision}</span>
                        )}
                      </td>
                      <td style={{ padding: '0.3rem' }}>
                        {tx.decision === 'REVIEW' && !tx.overridden ? (
                          <button className="btn-override" onClick={() => alert(`Override ${id}`)} style={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: '4px', padding: '0.05rem 0.3rem', fontSize: '0.55rem', cursor: 'pointer' }}>⚖</button>
                        ) : tx.overridden ? (
                          <span className="text-muted text-sm" style={{ fontSize: '0.5rem', color: 'var(--text-muted)' }}>by {tx.overridden_by || 'analyst'}</span>
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