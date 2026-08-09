import { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faChartLine, faClock, faExclamationTriangle, 
  faServer, faSync, faCheckCircle, faTimesCircle,
  faMicrochip, faMemory, faDatabase, faArrowUp, faArrowDown
} from '@fortawesome/free-solid-svg-icons';
import { getMonitoringStats, getApiLogs } from '../services/api';
import { formatDistanceToNow, format } from 'date-fns';
import StatCard from '../components/StatCard';
import StatusBadge from '../components/StatusBadge';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement,
  Filler,
} from 'chart.js';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import '../styles/monitoring.css';

// Register ChartJS
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement,
  Filler
);

export default function Monitoring() {
  const [stats, setStats] = useState(null);
  const [recentLogs, setRecentLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [error, setError] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statsRes, logsRes] = await Promise.all([
        getMonitoringStats(),
        getApiLogs({ limit: 10, offset: 0 })
      ]);
      setStats(statsRes.data);
      setRecentLogs(logsRes.data?.logs || []);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      console.error('Failed to fetch monitoring data:', err);
      setError('Failed to load monitoring data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !stats) {
    return (
      <div className="monitoring-container">
        <div className="monitoring-header">
          <h1>System Monitoring</h1>
          <p>Loading metrics...</p>
        </div>
        <div className="stats-grid">
          {[1,2,3,4].map(i => <StatCard key={i} loading />)}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="monitoring-container">
        <div className="error-state">
          <FontAwesomeIcon icon={faExclamationTriangle} />
          <p>{error}</p>
          <button className="btn-primary" onClick={fetchData}>Retry</button>
        </div>
      </div>
    );
  }

  const {
    total_requests_today = 0,
    error_rate = 0,
    avg_latency = 0,
    top_endpoints = [],
    users = [],
    system_health = { cpu_percent: 0, memory_used_mb: 0, memory_total_mb: 0, db_connections: 0 },
    auth_errors = 0,
    server_errors = 0,
    status = 'healthy'
  } = stats || {};

  const memoryPercent = system_health.memory_total_mb > 0 
    ? (system_health.memory_used_mb / system_health.memory_total_mb * 100)
    : 0;

  const isHealthy = server_errors === 0 && auth_errors < 5;

  // Chart data
  const topEndpointsData = {
    labels: top_endpoints.map(ep => ep.endpoint),
    datasets: [{
      label: 'Requests',
      data: top_endpoints.map(ep => ep.count),
      backgroundColor: 'rgba(59, 130, 246, 0.6)',
      borderColor: '#3b82f6',
      borderWidth: 1,
    }],
  };

  // Use real error split if available
  const successCount = total_requests_today - auth_errors - server_errors;
  const errorSplitData = {
    labels: ['Success (2xx)', 'Client Errors (4xx)', 'Server Errors (5xx)'],
    datasets: [{
      data: [
        successCount > 0 ? successCount : 1,
        auth_errors,
        server_errors
      ],
      backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
      borderWidth: 0,
    }],
  };

  const trendData = {
    labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', 'Now'],
    datasets: [{
      label: 'Requests / hour',
      data: [12, 8, 45, 78, 65, 32, 20],
      fill: true,
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      borderColor: '#3b82f6',
      tension: 0.4,
      pointRadius: 3,
    }],
  };

  const errors = recentLogs.filter(log => log.status_code >= 400);

  return (
    <div className="monitoring-container">
      <div className="monitoring-header">
        <div>
          <h1>System Monitoring</h1>
          <p className="monitoring-subtitle">Real-time health and performance observability</p>
        </div>
        <div className="monitoring-actions">
          <span className="last-updated">
            <FontAwesomeIcon icon={faSync} className={loading ? 'spinning' : ''} />
            Updated {formatDistanceToNow(lastUpdated)} ago
          </span>
          <button className="btn-primary" onClick={fetchData} disabled={loading}>
            <FontAwesomeIcon icon={faSync} /> Refresh
          </button>
        </div>
      </div>

      {/* Health Status Bar – now with separate indicators */}
      <div className="health-status-bar" style={{display:'flex', flexWrap:'wrap', gap:'1rem', padding:'1rem', background:'var(--surface2)', borderRadius:'8px'}}>
        <div className="health-item">
          <div className="health-icon">
            <FontAwesomeIcon icon={isHealthy ? faCheckCircle : faTimesCircle} />
          </div>
          <div>
            <div className="health-label">System Status</div>
            <div className={`health-value ${isHealthy ? 'healthy' : 'degraded'}`}>
              {isHealthy ? 'Operational' : 'Degraded'}
            </div>
          </div>
        </div>
        <div className="health-item">
          <div className="health-icon"><FontAwesomeIcon icon={faClock} /></div>
          <div>
            <div className="health-label">Avg Response</div>
            <div className="health-value">{avg_latency.toFixed(1)}ms</div>
          </div>
        </div>
        <div className="health-item">
          <div className="health-icon"><FontAwesomeIcon icon={faExclamationTriangle} /></div>
          <div>
            <div className="health-label">Server Errors (5xx)</div>
            <div className={`health-value ${server_errors === 0 ? 'healthy' : 'degraded'}`}>
              {server_errors}
            </div>
          </div>
        </div>
        <div className="health-item">
          <div className="health-icon"><FontAwesomeIcon icon={faExclamationTriangle} /></div>
          <div>
            <div className="health-label">Auth Errors (4xx)</div>
            <div className={`health-value ${auth_errors < 5 ? 'healthy' : 'degraded'}`}>
              {auth_errors}
            </div>
          </div>
        </div>
        <div className="health-item">
          <div className="health-icon"><FontAwesomeIcon icon={faMicrochip} /></div>
          <div>
            <div className="health-label">CPU Load</div>
            <div className={`health-value ${system_health.cpu_percent < 70 ? 'healthy' : 'degraded'}`}>
              {system_health.cpu_percent.toFixed(0)}%
            </div>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        <StatCard
          title="Total Requests"
          value={total_requests_today.toLocaleString()}
          icon={faChartLine}
          color="blue"
          subtitle="Today"
        />
        <StatCard
          title="Avg Latency"
          value={`${avg_latency.toFixed(1)}ms`}
          icon={faClock}
          color="teal"
          subtitle="Average response time"
        />
        <StatCard
          title="Error Rate"
          value={`${error_rate.toFixed(1)}%`}
          icon={faExclamationTriangle}
          color={error_rate < 5 ? 'green' : 'red'}
          subtitle="Of all requests"
        />
        <StatCard
          title="System Health"
          value={`${system_health.cpu_percent.toFixed(0)}%`}
          icon={faServer}
          color="purple"
          subtitle="CPU Usage"
        />
      </div>

      {/* Charts Row */}
      <div className="charts-row" style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(300px, 1fr))', gap:'1rem'}}>
        <div className="chart-card">
          <h3>Top Endpoints</h3>
          <div className="chart-wrapper" style={{height:'200px'}}>
            <Bar data={topEndpointsData} options={{ responsive: true, maintainAspectRatio: false }} />
          </div>
        </div>
        <div className="chart-card">
          <h3>Request Status</h3>
          <div className="chart-wrapper doughnut" style={{height:'200px'}}>
            <Doughnut data={errorSplitData} options={{ responsive: true, maintainAspectRatio: false }} />
          </div>
          <div className="chart-legend">
            <span><span className="dot success"></span> Success</span>
            <span><span className="dot warning"></span> Client Errors</span>
            <span><span className="dot danger"></span> Server Errors</span>
          </div>
        </div>
        <div className="chart-card">
          <h3>Request Trend (Last 24h)</h3>
          <div className="chart-wrapper" style={{height:'200px'}}>
            <Line data={trendData} options={{ responsive: true, maintainAspectRatio: false }} />
          </div>
        </div>
      </div>

      {/* System Health */}
      <div className="system-health-grid" style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(200px, 1fr))', gap:'1rem', marginTop:'1rem'}}>
        <div className="health-card">
          <div className="health-card-header">
            <FontAwesomeIcon icon={faMicrochip} />
            <span>CPU Usage</span>
          </div>
          <div className="health-card-value">{system_health.cpu_percent.toFixed(0)}%</div>
          <div className="health-bar-track">
            <div className={`health-bar ${system_health.cpu_percent > 70 ? 'warning' : ''}`} 
                 style={{ width: `${Math.min(system_health.cpu_percent, 100)}%` }} />
          </div>
        </div>

        <div className="health-card">
          <div className="health-card-header">
            <FontAwesomeIcon icon={faMemory} />
            <span>Memory</span>
          </div>
          <div className="health-card-value">{memoryPercent.toFixed(0)}%</div>
          <div className="health-bar-track">
            <div className={`health-bar ${memoryPercent > 80 ? 'warning' : ''}`} 
                 style={{ width: `${Math.min(memoryPercent, 100)}%` }} />
          </div>
          <div className="health-card-sub">
            {Math.round(system_health.memory_used_mb)} MB / {Math.round(system_health.memory_total_mb)} MB
          </div>
        </div>

        <div className="health-card">
          <div className="health-card-header">
            <FontAwesomeIcon icon={faDatabase} />
            <span>Database</span>
          </div>
          <div className="health-card-value">{system_health.db_connections}</div>
          <div className="health-card-sub">Active connections</div>
        </div>
      </div>

      {/* Recent Errors */}
      <div className="recent-errors">
        <h3>Recent Errors</h3>
        {errors.length === 0 ? (
          <div className="empty-state">No recent errors</div>
        ) : (
          <div className="error-list">
            {errors.slice(0, 5).map((log, idx) => (
              <div key={idx} className="error-item">
                <span className="error-time">{format(new Date(log.timestamp), 'HH:mm:ss')}</span>
                <span className="error-endpoint">{log.endpoint}</span>
                <StatusBadge status={log.status_code} />
                <span className="error-ip">{log.client_ip}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}