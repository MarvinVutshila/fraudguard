import './StatusBadge.css';

export default function StatusBadge({ status, label }) {
  const getStatusClass = () => {
    // If status is a string, map it directly
    if (typeof status === 'string') {
      const map = {
        'active': 'success',
        'approved': 'success',
        'pending': 'warning',
        'rejected': 'danger',
        'blocked': 'danger',
        'deleted': 'danger',
        'admin': 'primary',
        'analyst': 'info',
        'review': 'warning',
        'APPROVE': 'success',
        'BLOCK': 'danger',
        'REVIEW': 'warning',
      };
      return map[status.toLowerCase()] || 'default';
    }

    // If status is a number (HTTP status code)
    if (typeof status === 'number') {
      if (status >= 200 && status < 300) return 'success';
      if (status >= 300 && status < 400) return 'warning';
      if (status >= 400 && status < 500) return 'danger';
      if (status >= 500) return 'critical';
      return 'default';
    }

    return 'default';
  };

  // If label is provided, use it; otherwise show the status itself
  const displayLabel = label || status;

  return (
    <span className={`status-badge ${getStatusClass()}`}>
      {displayLabel}
    </span>
  );
}