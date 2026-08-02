import { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faSearch, faTimes, faChevronLeft, faChevronRight,
  faSync, faExclamationTriangle, faCheckCircle,
  faFilter, faDownload
} from '@fortawesome/free-solid-svg-icons';
import { getApiLogs } from '../services/api';
import { format } from 'date-fns';
import StatusBadge from '../components/StatusBadge';
import '../styles/monitoring.css';

export default function ApiLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({ page: 1, total: 0, limit: 50 });

  const fetchLogs = async (page = 1) => {
    setLoading(true);
    setError(null);
    try {
      const offset = (page - 1) * pagination.limit;
      const params = { limit: pagination.limit, offset };
      const res = await getApiLogs(params);
      setLogs(res.data?.logs || []);
      setPagination(prev => ({ 
        ...prev, 
        total: res.data?.total || 0, 
        page 
      }));
    } catch (err) {
      setError('Failed to load logs. Please try again.');
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs(1);
  }, []);

  const totalPages = Math.ceil(pagination.total / pagination.limit) || 1;

  return (
    <div className="monitoring-container api-logs-page">
      <div className="page-header">
        <div>
          <h1>API Request Logs</h1>
          <p className="page-subtitle">Monitor all API traffic to your fraud detection service</p>
        </div>
        <div className="page-actions">
          <button className="btn-secondary" onClick={fetchLogs} disabled={loading}>
            <FontAwesomeIcon icon={faSync} className={loading ? 'spinning' : ''} />
            Refresh
          </button>
          <button className="btn-secondary">
            <FontAwesomeIcon icon={faDownload} />
            Export
          </button>
        </div>
      </div>

      <div className="logs-summary">
        <span>{pagination.total} total requests</span>
        <span className="separator">•</span>
        <span>Showing {logs.length} results</span>
        {loading && <span className="loading-indicator">Loading...</span>}
      </div>

      {error ? (
        <div className="error-state">
          <FontAwesomeIcon icon={faExclamationTriangle} />
          <p>{error}</p>
          <button className="btn-primary" onClick={fetchLogs}>Retry</button>
        </div>
      ) : (
        <>
          <div className="table-wrapper">
            <table className="logs-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>User</th>
                  <th>Endpoint</th>
                  <th>Method</th>
                  <th>Status</th>
                  <th>Latency</th>
                  <th>IP</th>
                </tr>
              </thead>
              <tbody>
                {loading && logs.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="loading-cell">
                      <div className="spinner"></div>
                      <span>Loading logs...</span>
                    </td>
                  </tr>
                ) : logs.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="empty-cell">
                      <FontAwesomeIcon icon={faCheckCircle} />
                      <span>No logs found</span>
                      <span className="empty-hint">Make some API calls to see them here</span>
                    </td>
                  </tr>
                ) : (
                  logs.map(log => (
                    <tr key={log.id}>
                      <td className="timestamp-cell">
                        {format(new Date(log.timestamp), 'MMM d, HH:mm:ss')}
                      </td>
                      <td>{log.username || 'Anonymous'}</td>
                      <td className="endpoint-cell">{log.endpoint}</td>
                      <td>
                        <span className={`method-badge ${log.method.toLowerCase()}`}>
                          {log.method}
                        </span>
                      </td>
                      <td>
                        <StatusBadge status={log.status_code} />
                      </td>
                      <td>
                        <span className={`latency ${log.response_time > 500 ? 'slow' : log.response_time > 200 ? 'medium' : 'fast'}`}>
                          {log.response_time}ms
                        </span>
                      </td>
                      <td className="ip-cell">{log.client_ip}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="pagination-bar">
            <button 
              className="pagination-btn" 
              disabled={pagination.page <= 1} 
              onClick={() => fetchLogs(pagination.page - 1)}
            >
              <FontAwesomeIcon icon={faChevronLeft} /> Previous
            </button>
            <span className="pagination-info">
              Page {pagination.page} of {totalPages}
            </span>
            <button 
              className="pagination-btn" 
              disabled={pagination.page >= totalPages} 
              onClick={() => fetchLogs(pagination.page + 1)}
            >
              Next <FontAwesomeIcon icon={faChevronRight} />
            </button>
          </div>
        </>
      )}
    </div>
  );
}