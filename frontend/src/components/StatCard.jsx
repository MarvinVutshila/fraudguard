import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faArrowUp,
  faArrowDown,
} from '@fortawesome/free-solid-svg-icons';
import './StatCard.css';

export default function StatCard({
  title,
  value,
  icon,
  color = 'blue',
  subtitle,
  trend,
  loading = false
}) {
  const colorMap = {
    blue: { bg: 'rgba(59,130,246,0.08)', icon: '#3b82f6' },
    green: { bg: 'rgba(16,185,129,0.08)', icon: '#10b981' },
    red: { bg: 'rgba(239,68,68,0.08)', icon: '#ef4444' },
    purple: { bg: 'rgba(139,92,246,0.08)', icon: '#8b5cf6' },
    orange: { bg: 'rgba(245,158,11,0.08)', icon: '#f59e0b' },
    teal: { bg: 'rgba(20,184,166,0.08)', icon: '#14b8a6' },
  };

  const styles = colorMap[color] || colorMap.blue;

  if (loading) {
    return (
      <div className="stat-card loading">
        <div className="stat-card-skeleton">
          <div className="skeleton-icon"></div>
          <div className="skeleton-content">
            <div className="skeleton-title"></div>
            <div className="skeleton-value"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="stat-card">
      <div className="stat-card-inner">
        <div className="stat-card-icon" style={{ background: styles.bg, color: styles.icon }}>
          <FontAwesomeIcon icon={icon} />
        </div>
        <div className="stat-card-content">
          <span className="stat-card-title">{title}</span>
          <span className="stat-card-value">{value}</span>
          {subtitle && <span className="stat-card-subtitle">{subtitle}</span>}
          {trend && (
            <div className={`stat-card-trend ${trend.isPositive ? 'positive' : 'negative'}`}>
              <FontAwesomeIcon icon={trend.isPositive ? faArrowUp : faArrowDown} />
              {trend.value}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}