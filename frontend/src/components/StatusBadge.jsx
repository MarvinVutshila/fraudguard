import './StatusBadge.css';

export default function StatusBadge({ status, label }) {
  const getStatusClass = () => {
    if (status >= 200 && status < 300) return 'success';
    if (status >= 300 && status < 400) return 'warning';
    if (status >= 400 && status < 500) return 'error';
    if (status >= 500) return 'critical';
    return 'default';
  };

  return (
    <span className={`status-badge ${getStatusClass()}`}>
      {label || status}
    </span>
  );
}