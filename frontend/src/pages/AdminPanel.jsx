import { useState, useEffect, useCallback, useRef } from 'react';
import api from '../services/api';
import { useTheme } from '../context/ThemeContext';

// ─────────────────────────────────────────────────────────────────────────────
// Tiny utilities
// ─────────────────────────────────────────────────────────────────────────────

const fmt = (ts) =>
  ts ? new Date(ts).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '—';

const ago = (ts) => {
  if (!ts) return '—';
  const diff = Date.now() - new Date(ts).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'Just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
};

const ROLE_COLORS = {
  admin: '#a78bfa',
  analyst: '#60a5fa',
  viewer: '#6ee7b7',
};

const STATUS_COLORS = {
  active: '#34d399',
  pending: '#fbbf24',
  rejected: '#f87171',
  blocked: '#ef4444',
  deleted: '#6b7280',
};

const SEVERITY_COLORS = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#10b981',
};

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components (with dark mode support)
// ─────────────────────────────────────────────────────────────────────────────

function StatCard({ icon, label, value, sub, color = 'var(--purple)' }) {
  return (
    <div style={{
      background: 'var(--card-bg)',
      border: `1px solid ${color}33`,
      borderRadius: 12,
      padding: '1.25rem 1.5rem',
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
      position: 'relative',
      overflow: 'hidden',
    }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: color, borderRadius: '12px 12px 0 0' }} />
      <div style={{ fontSize: '1.6rem', marginBottom: 2 }}>{icon}</div>
      <div style={{ fontSize: '2rem', fontWeight: 700, color, letterSpacing: '-0.03em', lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      {sub && <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function Badge({ status }) {
  const color = STATUS_COLORS[status] || '#8892a4';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      background: color + '1a', border: `1px solid ${color}44`,
      color, borderRadius: 6, padding: '2px 8px',
      fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase',
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: color }} />
      {status}
    </span>
  );
}

function RoleBadge({ role }) {
  const color = ROLE_COLORS[role] || '#8892a4';
  return (
    <span style={{
      background: color + '1a', border: `1px solid ${color}44`,
      color, borderRadius: 6, padding: '2px 8px',
      fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase',
    }}>
      {role || 'analyst'}
    </span>
  );
}

function SeverityBadge({ severity }) {
  const color = SEVERITY_COLORS[severity] || '#8892a4';
  return (
    <span style={{
      background: color + '1a', border: `1px solid ${color}55`,
      color, borderRadius: 6, padding: '2px 8px',
      fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase',
    }}>
      {severity}
    </span>
  );
}

function Spinner() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '3rem' }}>
      <div style={{
        width: 32, height: 32, borderRadius: '50%',
        border: '3px solid var(--purple, #7c3aed)',
        borderTopColor: 'transparent',
        animation: 'spin 0.7s linear infinite',
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function EmptyState({ icon = '📭', text }) {
  return (
    <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
      <div style={{ fontSize: '2.5rem', marginBottom: 8 }}>{icon}</div>
      <div style={{ fontSize: '0.9rem' }}>{text}</div>
    </div>
  );
}

function Pagination({ page, totalPages, onPage }) {
  if (totalPages <= 1) return null;
  const pages = [];
  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || (i >= page - 2 && i <= page + 2)) {
      pages.push(i);
    } else if (pages[pages.length - 1] !== '…') {
      pages.push('…');
    }
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'center', padding: '1rem 0 0.5rem' }}>
      <PaginationBtn disabled={page === 1} onClick={() => onPage(page - 1)}>‹ Prev</PaginationBtn>
      {pages.map((p, i) =>
        p === '…' ? (
          <span key={i} style={{ color: 'var(--text-muted)', padding: '0 4px' }}>…</span>
        ) : (
          <PaginationBtn key={i} active={p === page} onClick={() => onPage(p)}>{p}</PaginationBtn>
        )
      )}
      <PaginationBtn disabled={page === totalPages} onClick={() => onPage(page + 1)}>Next ›</PaginationBtn>
    </div>
  );
}

function PaginationBtn({ children, onClick, disabled, active }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: '5px 12px', borderRadius: 7,
        background: active ? 'var(--purple, #7c3aed)' : 'transparent',
        border: `1px solid ${active ? 'var(--purple)' : 'var(--border)'}`,
        color: active ? '#fff' : disabled ? 'var(--text-muted)' : 'var(--text)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        fontSize: '0.8rem', fontWeight: 500,
        opacity: disabled ? 0.4 : 1,
        transition: 'all 0.15s',
      }}
    >
      {children}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Modal
// ─────────────────────────────────────────────────────────────────────────────

function Modal({ title, onClose, children, width = 620 }) {
  const overlayRef = useRef();
  useEffect(() => {
    const handler = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div
      ref={overlayRef}
      onClick={(e) => e.target === overlayRef.current && onClose()}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '1rem',
        animation: 'fadeIn 0.15s ease',
      }}
    >
      <style>{`@keyframes fadeIn{from{opacity:0;transform:scale(.97)}to{opacity:1;transform:scale(1)}}`}</style>
      <div style={{
        background: 'var(--card-bg)',
        border: '1px solid var(--border)',
        borderRadius: 16, width: '100%', maxWidth: width,
        maxHeight: '90vh', overflowY: 'auto',
        boxShadow: 'var(--shadow)',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '1.25rem 1.5rem',
          borderBottom: '1px solid var(--border)',
        }}>
          <div style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--text)' }}>{title}</div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent', border: 'none', cursor: 'pointer',
              color: 'var(--text-muted)', fontSize: '1.3rem', lineHeight: 1,
              padding: '2px 6px', borderRadius: 6,
            }}
          >×</button>
        </div>
        <div style={{ padding: '1.5rem' }}>{children}</div>
      </div>
    </div>
  );
}

function ConfirmModal({ message, subtext, onConfirm, onCancel, danger = true, label = 'Confirm', extraField }) {
  const [extra, setExtra] = useState('');
  return (
    <Modal title={danger ? '⚠️ Confirm Action' : 'Confirm Action'} onClose={onCancel} width={440}>
      <div style={{ color: 'var(--text)', marginBottom: 12 }}>{message}</div>
      {subtext && <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 16 }}>{subtext}</div>}
      {extraField && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', fontSize: '0.8rem', marginBottom: 6, color: 'var(--text-muted)' }}>
            {extraField.label}
          </label>
          <input
            value={extra}
            onChange={(e) => setExtra(e.target.value)}
            placeholder={extraField.placeholder}
            style={{
              width: '100%', boxSizing: 'border-box',
              background: 'var(--bg)', border: '1px solid var(--border)',
              borderRadius: 8, padding: '8px 12px', color: 'var(--text)', fontSize: '0.9rem',
            }}
          />
        </div>
      )}
      <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
        <button className="btn-secondary" onClick={onCancel}>Cancel</button>
        <button
          onClick={() => onConfirm(extra)}
          style={{
            padding: '8px 20px', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600,
            background: danger ? '#ef4444' : 'var(--purple, #7c3aed)', color: '#fff', fontSize: '0.9rem',
          }}
        >
          {label}
        </button>
      </div>
    </Modal>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// User Detail Modal
// ─────────────────────────────────────────────────────────────────────────────

function UserDetailModal({ user, onClose }) {
  const [activity, setActivity] = useState(null);
  const [loadingActivity, setLoadingActivity] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get(`/admin/users/${user.id}/activity`);
        setActivity(res.data);
      } catch {
        setActivity(null);
      } finally {
        setLoadingActivity(false);
      }
    })();
  }, [user.id]);

  const tabs = ['overview', 'activity', 'logins'];

  return (
    <Modal title={`👤 ${user.username}`} onClose={onClose} width={700}>
      <div style={{ display: 'flex', gap: 6, marginBottom: 20 }}>
        {tabs.map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            style={{
              padding: '6px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
              fontWeight: 600, fontSize: '0.82rem', textTransform: 'capitalize',
              background: activeTab === t ? 'var(--purple, #7c3aed)' : 'var(--border)',
              color: activeTab === t ? '#fff' : 'var(--text-muted)',
              transition: 'all 0.15s',
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {[
            ['ID', user.id],
            ['Username', user.username],
            ['Role', <RoleBadge role={user.role} />],
            ['Status', <Badge status={user.status} />],
            ['Created', fmt(user.created_at)],
            ['Last Active', ago(user.last_active)],
            ['Recent Failed Logins', user.recent_failed_logins ?? 0],
          ].map(([k, v]) => (
            <div key={k} style={{ background: 'var(--bg)', borderRadius: 10, padding: '12px 14px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{k}</div>
              <div style={{ fontWeight: 500, color: 'var(--text)' }}>{v}</div>
            </div>
          ))}
          {user.blocked_reason && (
            <div style={{ gridColumn: '1 / -1', background: '#ef444414', border: '1px solid #ef444433', borderRadius: 10, padding: '12px 14px' }}>
              <div style={{ fontSize: '0.7rem', color: '#ef4444', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Block Reason</div>
              <div style={{ color: '#ef4444' }}>{user.blocked_reason}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>Blocked {fmt(user.blocked_at)}</div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'activity' && (
        loadingActivity ? <Spinner /> : !activity?.activity?.length ? (
          <EmptyState icon="📋" text="No activity records found for this user" />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {activity.activity.map((a, i) => (
              <div key={i} style={{
                background: 'var(--bg)', borderRadius: 10, padding: '12px 14px',
                borderLeft: '3px solid var(--purple, #7c3aed)',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text)', fontSize: '0.85rem' }}>{a.action}</span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{fmt(a.timestamp)}</span>
                </div>
                {a.details && (
                  <pre style={{ margin: '6px 0 0', fontSize: '0.72rem', color: 'var(--text-muted)', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                    {typeof a.details === 'string' ? a.details : JSON.stringify(a.details, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )
      )}

      {activeTab === 'logins' && (
        loadingActivity ? <Spinner /> : !activity?.login_logs?.length ? (
          <EmptyState icon="🔑" text="No login records found" />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
              <thead>
                <tr>
                  {['Status', 'IP Address', 'Device', 'Time'].map((h) => (
                    <th key={h} style={{ textAlign: 'left', padding: '8px 10px', color: 'var(--text-muted)', fontWeight: 600, borderBottom: '1px solid var(--border)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {activity.login_logs.map((l, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '8px 10px' }}>
                      {l.success
                        ? <span style={{ color: '#34d399', fontWeight: 600 }}>✓ Success</span>
                        : <span style={{ color: '#ef4444', fontWeight: 600 }}>✗ Failed</span>}
                    </td>
                    <td style={{ padding: '8px 10px', fontFamily: 'monospace', color: 'var(--text-muted)' }}>{l.ip || '—'}</td>
                    <td style={{ padding: '8px 10px', color: 'var(--text-muted)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={l.user_agent}>{l.user_agent || '—'}</td>
                    <td style={{ padding: '8px 10px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{fmt(l.timestamp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </Modal>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Role Edit Modal
// ─────────────────────────────────────────────────────────────────────────────

function RoleModal({ user, onClose, onSaved }) {
  const [role, setRole] = useState(user.role || 'analyst');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.patch(`/admin/users/${user.id}/role`, { role });
      onSaved();
      onClose();
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to update role');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={`Change Role — ${user.username}`} onClose={onClose} width={400}>
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', fontSize: '0.8rem', marginBottom: 6, color: 'var(--text-muted)' }}>New Role</label>
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          style={{
            width: '100%', background: 'var(--bg)',
            border: '1px solid var(--border)', borderRadius: 8,
            padding: '10px 12px', color: 'var(--text)', fontSize: '0.9rem',
          }}
        >
          <option value="admin">Admin</option>
          <option value="analyst">Analyst</option>
          <option value="viewer">Viewer</option>
        </select>
      </div>
      {error && <div style={{ color: '#ef4444', fontSize: '0.85rem', marginBottom: 12 }}>{error}</div>}
      <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
        <button className="btn-secondary" onClick={onClose}>Cancel</button>
        <button onClick={save} disabled={saving} className="btn-success">
          {saving ? 'Saving…' : 'Save Role'}
        </button>
      </div>
    </Modal>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Alerts Panel
// ─────────────────────────────────────────────────────────────────────────────

function AlertsPanel({ onAck }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [acknowledging, setAcknowledging] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/security/alerts');
      setAlerts(res.data.alerts || []);
    } catch {
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const ack = async (alertId) => {
    setAcknowledging(alertId);
    try {
      await api.post(`/admin/security/acknowledge/${alertId}`, { note: '' });
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
      onAck?.();
    } catch {
      /* ignore */
    } finally {
      setAcknowledging(null);
    }
  };

  if (loading) return <Spinner />;
  if (!alerts.length) return <EmptyState icon="✅" text="No active security alerts" />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {alerts.map((a) => {
        const color = SEVERITY_COLORS[a.severity] || '#8892a4';
        return (
          <div key={a.id} style={{
            background: 'var(--bg)',
            border: `1px solid ${color}44`,
            borderLeft: `4px solid ${color}`,
            borderRadius: 10, padding: '14px 16px',
            display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12,
          }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <span style={{ fontSize: '1.1rem' }}>
                  {a.type === 'brute_force' ? '🔨' : '📍'}
                </span>
                <span style={{ fontWeight: 700, color: 'var(--text)', fontSize: '0.9rem' }}>
                  {a.type === 'brute_force' ? 'Brute Force Detected' : 'Location Anomaly'}
                </span>
                <SeverityBadge severity={a.severity} />
              </div>
              <div style={{ color: 'var(--text)', fontSize: '0.85rem', marginBottom: 4 }}>
                <span style={{ color: 'var(--purple, #7c3aed)', fontWeight: 600 }}>@{a.username}</span>
                {' — '}{a.message}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{fmt(a.timestamp)}</div>
            </div>
            <button
              onClick={() => ack(a.id)}
              disabled={acknowledging === a.id}
              style={{
                padding: '6px 14px', borderRadius: 8, border: '1px solid var(--border)',
                background: 'transparent', cursor: 'pointer', fontWeight: 600,
                color: 'var(--text-muted)', fontSize: '0.8rem', whiteSpace: 'nowrap',
                transition: 'all 0.15s',
              }}
            >
              {acknowledging === a.id ? '…' : '✓ Dismiss'}
            </button>
          </div>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Users Table Tab with ADMIN PROTECTION and EXPORT
// ─────────────────────────────────────────────────────────────────────────────

function UsersTable({ onRefreshSummary }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [searchInput, setSearchInput] = useState('');

  const [viewUser, setViewUser] = useState(null);
  const [editRoleUser, setEditRoleUser] = useState(null);
  const [confirmAction, setConfirmAction] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [toast, setToast] = useState(null);

  const showToast = (msg, ok = true) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3500);
  };

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/users', {
        params: { page, page_size: 15, search: search || undefined, role: roleFilter || undefined, status: statusFilter || undefined },
      });
      setUsers(res.data.users || []);
      setTotal(res.data.total || 0);
      setTotalPages(res.data.total_pages || 1);
    } catch {
      setUsers([]);
    } finally {
      setLoading(false);
    }
  }, [page, search, roleFilter, statusFilter]);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const searchTimer = useRef();
  const handleSearchInput = (val) => {
    setSearchInput(val);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      setSearch(val);
      setPage(1);
    }, 350);
  };

  // ========== EXPORT USERS ==========
  const exportUsersCSV = async () => {
    try {
      showToast('Exporting users...', true);
      const response = await api.get('/admin/export/users', {
        params: { search, role: roleFilter, status: statusFilter },
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `users_export_${new Date().toISOString().slice(0,10)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      showToast('Users exported successfully!', true);
    } catch (err) {
      console.error('Export failed:', err);
      showToast('Failed to export users: ' + (err.response?.data?.detail || err.message), false);
    }
  };

  // ═══════════════════════════════════════════════════════════
  // 🔒 ADMIN PROTECTION: Block destructive actions on admins
  // ═══════════════════════════════════════════════════════════
  const executeAction = async (type, user, extra) => {
    // 🔒 CRITICAL: Prevent any action on admin users
    if (user.role === 'admin') {
      showToast('⚠️ Admin users cannot be modified, removed, or blocked for security reasons.', false);
      setConfirmAction(null);
      return;
    }

    setActionLoading(true);
    try {
      if (type === 'block') {
        await api.post(`/admin/users/${user.id}/block`, { reason: extra || null });
        showToast(`@${user.username} has been blocked`);
      } else if (type === 'unblock') {
        await api.post(`/admin/users/${user.id}/unblock`);
        showToast(`@${user.username} has been unblocked`, true);
      } else if (type === 'delete') {
        await api.delete(`/admin/users/${user.id}`);
        showToast(`@${user.username} has been deleted`);
      }
      setConfirmAction(null);
      await loadUsers();
      onRefreshSummary?.();
    } catch (e) {
      showToast(e.response?.data?.detail || 'Action failed', false);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div>
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 2000,
          background: toast.ok ? '#065f46' : '#7f1d1d',
          border: `1px solid ${toast.ok ? '#34d399' : '#ef4444'}`,
          borderRadius: 10, padding: '12px 20px', color: '#fff', fontWeight: 600,
          boxShadow: '0 8px 30px rgba(0,0,0,0.4)', animation: 'fadeIn 0.2s',
        }}>
          {toast.ok ? '✓' : '✗'} {toast.msg}
        </div>
      )}

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16, alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: '1 1 200px' }}>
          <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }}>🔍</span>
          <input
            value={searchInput}
            onChange={(e) => handleSearchInput(e.target.value)}
            placeholder="Search username…"
            style={{
              width: '100%', boxSizing: 'border-box',
              background: 'var(--bg)', border: '1px solid var(--border)',
              borderRadius: 9, padding: '9px 12px 9px 36px', color: 'var(--text)', fontSize: '0.87rem',
            }}
          />
        </div>
        <FilterSelect value={roleFilter} onChange={(v) => { setRoleFilter(v); setPage(1); }} options={['', 'admin', 'analyst', 'viewer']} labels={['All Roles', 'Admin', 'Analyst', 'Viewer']} />
        <FilterSelect value={statusFilter} onChange={(v) => { setStatusFilter(v); setPage(1); }} options={['', 'active', 'pending', 'blocked', 'rejected', 'deleted']} labels={['All Statuses', 'Active', 'Pending', 'Blocked', 'Rejected', 'Deleted']} />
        <button className="btn-secondary" onClick={() => { setSearch(''); setSearchInput(''); setRoleFilter(''); setStatusFilter(''); setPage(1); }}>
          ↺ Clear
        </button>
        {/* ✅ EXPORT BUTTON */}
        <button className="btn-success" onClick={exportUsersCSV}>
          ⬇ Export CSV
        </button>
        <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginLeft: 'auto' }}>
          {total} user{total !== 1 ? 's' : ''}
        </span>
      </div>

      {loading ? <Spinner /> : users.length === 0 ? (
        <EmptyState icon="👥" text="No users match your filters" />
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr>
                {['User', 'Role', 'Status', 'Last Active', 'Failed Logins', 'Created', 'Actions'].map((h) => (
                  <th key={h} style={{
                    textAlign: 'left', padding: '10px 12px', color: 'var(--text-muted)',
                    fontWeight: 600, fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.06em',
                    borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isAdmin = u.role === 'admin';
                return (
                  <tr key={u.id} style={{ borderBottom: '1px solid var(--border)', transition: 'background 0.1s' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '12px 12px' }}>
                      <div style={{ fontWeight: 700, color: 'var(--text)' }}>@{u.username}</div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>ID #{u.id}</div>
                      {isAdmin && (
                        <div style={{ fontSize: '0.6rem', color: 'var(--purple)', fontWeight: 700, marginTop: 2 }}>
                          🔒 Protected
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '12px 12px' }}><RoleBadge role={u.role} /></td>
                    <td style={{ padding: '12px 12px' }}><Badge status={u.status} /></td>
                    <td style={{ padding: '12px 12px', color: 'var(--text-muted)', whiteSpace: 'nowrap', fontSize: '0.8rem' }}>{ago(u.last_active)}</td>
                    <td style={{ padding: '12px 12px', textAlign: 'center' }}>
                      {u.recent_failed_logins > 5
                        ? <span style={{ color: '#ef4444', fontWeight: 700 }}>🔴 {u.recent_failed_logins}</span>
                        : u.recent_failed_logins > 0
                          ? <span style={{ color: '#f59e0b', fontWeight: 600 }}>⚠️ {u.recent_failed_logins}</span>
                          : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                    </td>
                    <td style={{ padding: '12px 12px', color: 'var(--text-muted)', whiteSpace: 'nowrap', fontSize: '0.8rem' }}>{fmt(u.created_at)}</td>
                    <td style={{ padding: '12px 12px' }}>
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        <ActionBtn onClick={() => setViewUser(u)} title="View details">👁</ActionBtn>
                        <ActionBtn 
                          onClick={() => isAdmin ? showToast('⚠️ Admin users cannot be edited', false) : setEditRoleUser(u)} 
                          title={isAdmin ? 'Admin protected' : 'Edit role'} 
                          disabled={isAdmin}
                          color={isAdmin ? 'var(--text-faint)' : undefined}
                        >
                          ✏️
                        </ActionBtn>
                        {u.status === 'blocked'
                          ? <ActionBtn 
                              onClick={() => isAdmin ? showToast('⚠️ Admin users cannot be unblocked', false) : setConfirmAction({ type: 'unblock', user: u })} 
                              title={isAdmin ? 'Admin protected' : 'Unblock'} 
                              color="#34d399"
                              disabled={isAdmin}
                            >🔓</ActionBtn>
                          : <ActionBtn 
                              onClick={() => isAdmin ? showToast('⚠️ Admin users cannot be blocked', false) : setConfirmAction({ type: 'block', user: u })} 
                              title={isAdmin ? 'Admin protected' : 'Block'} 
                              color={isAdmin ? 'var(--text-faint)' : '#f59e0b'}
                              disabled={isAdmin || u.status === 'deleted'}
                            >🔒</ActionBtn>
                        }
                        <ActionBtn 
                          onClick={() => isAdmin ? showToast('⚠️ Admin users cannot be deleted', false) : setConfirmAction({ type: 'delete', user: u })} 
                          title={isAdmin ? 'Admin protected' : 'Delete'} 
                          color={isAdmin ? 'var(--text-faint)' : '#ef4444'}
                          disabled={isAdmin || u.status === 'deleted'}
                        >🗑</ActionBtn>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <Pagination page={page} totalPages={totalPages} onPage={setPage} />

      {/* 🔒 Security Notice */}
      <div style={{
        marginTop: 16,
        padding: '12px 16px',
        background: 'var(--warning)11',
        border: '1px solid var(--warning)33',
        borderRadius: 8,
        color: 'var(--text-muted)',
        fontSize: '0.8rem',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        <span style={{ fontSize: '1.2rem' }}>🔒</span>
        <span>
          <strong style={{ color: 'var(--text)' }}>Security Notice:</strong> 
          Admin accounts are <strong>protected</strong> from deletion, modification, and blocking for system integrity.
        </span>
      </div>

      {/* Modals */}
      {viewUser && <UserDetailModal user={viewUser} onClose={() => setViewUser(null)} />}
      {editRoleUser && (
        <RoleModal
          user={editRoleUser}
          onClose={() => setEditRoleUser(null)}
          onSaved={() => { loadUsers(); onRefreshSummary?.(); }}
        />
      )}
      {confirmAction?.type === 'block' && (
        <ConfirmModal
          message={`Block @${confirmAction.user.username}?`}
          subtext="This will prevent the user from logging in."
          danger
          label="Block User"
          extraField={{ label: 'Reason (optional)', placeholder: 'Why are you blocking this user?' }}
          onConfirm={(reason) => executeAction('block', confirmAction.user, reason)}
          onCancel={() => setConfirmAction(null)}
        />
      )}
      {confirmAction?.type === 'unblock' && (
        <ConfirmModal
          message={`Unblock @${confirmAction.user.username}?`}
          subtext="The user will be able to log in again."
          danger={false}
          label="Unblock User"
          onConfirm={() => executeAction('unblock', confirmAction.user)}
          onCancel={() => setConfirmAction(null)}
        />
      )}
      {confirmAction?.type === 'delete' && (
        <ConfirmModal
          message={`Delete @${confirmAction.user.username}?`}
          subtext="The account will be soft-deleted and the user will no longer be able to log in."
          danger
          label="Delete User"
          onConfirm={() => executeAction('delete', confirmAction.user)}
          onCancel={() => setConfirmAction(null)}
        />
      )}
    </div>
  );
}

function ActionBtn({ children, onClick, title, color = 'var(--text-muted)', disabled }) {
  return (
    <button
      onClick={disabled ? undefined : onClick}
      title={title}
      disabled={disabled}
      style={{
        padding: '5px 9px', borderRadius: 7,
        background: disabled ? 'var(--surface3)' : 'var(--bg)',
        border: `1px solid ${disabled ? 'var(--border)' : 'var(--border)'}`,
        cursor: disabled ? 'not-allowed' : 'pointer', fontSize: '0.85rem',
        color: disabled ? 'var(--text-faint)' : color,
        opacity: disabled ? 0.4 : 1, transition: 'all 0.15s',
      }}
    >
      {children}
    </button>
  );
}

function FilterSelect({ value, onChange, options, labels }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{
        background: 'var(--bg)', border: '1px solid var(--border)',
        borderRadius: 9, padding: '9px 12px', color: 'var(--text)', fontSize: '0.87rem', cursor: 'pointer',
      }}
    >
      {options.map((o, i) => <option key={o} value={o}>{labels[i]}</option>)}
    </select>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Login Logs Tab with EXPORT
// ─────────────────────────────────────────────────────────────────────────────

function LoginLogsTab() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [usernameFilter, setUsernameFilter] = useState('');
  const [inputVal, setInputVal] = useState('');
  const [exporting, setExporting] = useState(false);
  const searchTimer = useRef();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/login-logs', {
        params: { page, page_size: 30, username: usernameFilter || undefined },
      });
      const data = res.data;
      if (Array.isArray(data)) {
        setLogs(data);
        setTotal(data.length);
        setTotalPages(1);
      } else {
        setLogs(data.logs || []);
        setTotal(data.total || 0);
        setTotalPages(data.total_pages || 1);
      }
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [page, usernameFilter]);

  useEffect(() => { load(); }, [load]);

  const handleInput = (val) => {
    setInputVal(val);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => { setUsernameFilter(val); setPage(1); }, 350);
  };

  // ========== EXPORT LOGIN LOGS ==========
  const exportLoginLogsCSV = async () => {
    setExporting(true);
    try {
      const response = await api.get('/admin/export/login-logs', {
        params: { username: usernameFilter || undefined },
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `login_logs_${new Date().toISOString().slice(0,10)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
      alert('Failed to export login logs: ' + (err.response?.data?.detail || err.message));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16, alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: '1 1 200px' }}>
          <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }}>🔍</span>
          <input
            value={inputVal}
            onChange={(e) => handleInput(e.target.value)}
            placeholder="Filter by username…"
            style={{
              width: '100%', boxSizing: 'border-box',
              background: 'var(--bg)', border: '1px solid var(--border)',
              borderRadius: 9, padding: '9px 12px 9px 36px', color: 'var(--text)', fontSize: '0.87rem',
            }}
          />
        </div>
        <button className="btn-secondary" onClick={load}>↺ Refresh</button>
        {/* ✅ EXPORT BUTTON */}
        <button className="btn-success" onClick={exportLoginLogsCSV} disabled={exporting || logs.length === 0}>
          {exporting ? 'Exporting…' : '⬇ Export CSV'}
        </button>
        <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginLeft: 'auto' }}>
          {total} record{total !== 1 ? 's' : ''}
        </span>
      </div>

      {loading ? <Spinner /> : logs.length === 0 ? (
        <EmptyState icon="📋" text="No login logs found" />
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.83rem' }}>
            <thead>
              <tr>
                {['Username', 'Result', 'IP Address', 'Device / Agent', 'Timestamp'].map((h) => (
                  <th key={h} style={{
                    textAlign: 'left', padding: '10px 12px', color: 'var(--text-muted)',
                    fontWeight: 600, fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.06em',
                    borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {logs.map((log, i) => (
                <tr key={log.id || i} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--text)' }}>{log.username || '—'}</td>
                  <td style={{ padding: '10px 12px' }}>
                    {log.success
                      ? <span style={{ color: '#34d399', fontWeight: 600, fontSize: '0.8rem' }}>✓ Success</span>
                      : <span style={{ color: '#ef4444', fontWeight: 600, fontSize: '0.8rem' }}>✗ Failed</span>}
                  </td>
                  <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {log.ip_address || log.ip || '—'}
                  </td>
                  <td style={{
                    padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.75rem',
                    maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }} title={log.user_agent}>{log.user_agent || '—'}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-muted)', whiteSpace: 'nowrap', fontSize: '0.8rem' }}>
                    {fmt(log.timestamp)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pagination page={page} totalPages={totalPages} onPage={setPage} />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Pending Approvals Tab
// ─────────────────────────────────────────────────────────────────────────────

function PendingTab({ onRefreshSummary }) {
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/users/pending');
      setPending(res.data?.pending || []);
    } catch {
      setPending([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleApproval = async (userId, approve) => {
    try {
      await api.post('/admin/users/approve', { user_id: userId, approve });
      load();
      onRefreshSummary?.();
    } catch (e) {
      alert('Action failed: ' + (e.response?.data?.detail || e.message));
    }
  };

  if (loading) return <Spinner />;
  if (!pending.length) return <EmptyState icon="✅" text="No pending registrations — all caught up!" />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {pending.map((u) => (
        <div key={u.id} style={{
          background: 'var(--bg)', border: '1px solid var(--border)',
          borderRadius: 12, padding: '14px 18px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{
              width: 42, height: 42, borderRadius: 10, background: 'var(--purple, #7c3aed)22',
              border: '1px solid var(--purple, #7c3aed)44', display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '1.2rem', flexShrink: 0,
            }}>👤</div>
            <div>
              <div style={{ fontWeight: 700, color: 'var(--text)', marginBottom: 2 }}>@{u.username}</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>ID #{u.id}</span>
                <Badge status="pending" />
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Registered {fmt(u.created_at)}</span>
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn-success" onClick={() => handleApproval(u.id, true)}>✓ Approve</button>
            <button className="btn-danger" onClick={() => handleApproval(u.id, false)}>✗ Reject</button>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Overview Tab
// ─────────────────────────────────────────────────────────────────────────────

function OverviewTab({ summary, onNavigate }) {
  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--text)', marginBottom: 4 }}>Welcome to the Admin Centre</div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.87rem' }}>
          Use the tabs above to manage users, review security alerts, and audit login activity across FraudGuard.
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: 14 }}>
        {[
          {
            icon: '⏳', title: 'Pending Approvals',
            desc: summary?.pending_approvals
              ? `${summary.pending_approvals} account${summary.pending_approvals !== 1 ? 's' : ''} awaiting your review`
              : 'No pending registrations',
            action: 'Review Now', tab: 'pending',
            highlight: summary?.pending_approvals > 0,
            color: '#fbbf24',
          },
          {
            icon: '🚨', title: 'Security Alerts',
            desc: summary?.high_risk_users
              ? `${summary.high_risk_users} high-risk user${summary.high_risk_users !== 1 ? 's' : ''} detected`
              : 'No active security alerts',
            action: 'View Alerts', tab: 'alerts',
            highlight: summary?.high_risk_users > 0,
            color: '#ef4444',
          },
          {
            icon: '👥', title: 'User Management',
            desc: `${summary?.total_users ?? 0} total users — ${summary?.blocked_users ?? 0} blocked`,
            action: 'Manage Users', tab: 'users',
            highlight: false,
            color: '#60a5fa',
          },
          {
            icon: '📋', title: 'Login Audit Logs',
            desc: `${summary?.failed_logins_24h ?? 0} failed login attempts in the last 24 hours`,
            action: 'View Logs', tab: 'logs',
            highlight: (summary?.failed_logins_24h ?? 0) > 10,
            color: '#a78bfa',
          },
        ].map((card) => (
          <div
            key={card.tab}
            style={{
              background: 'var(--bg)',
              border: `1px solid ${card.highlight ? card.color + '66' : 'var(--border)'}`,
              borderRadius: 12, padding: '18px 20px',
              display: 'flex', flexDirection: 'column', gap: 10,
              position: 'relative', overflow: 'hidden',
            }}
          >
            {card.highlight && (
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: card.color }} />
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: '1.4rem' }}>{card.icon}</span>
              <span style={{ fontWeight: 700, color: 'var(--text)', fontSize: '0.95rem' }}>{card.title}</span>
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.84rem', flex: 1 }}>{card.desc}</div>
            <button
              onClick={() => onNavigate(card.tab)}
              style={{
                padding: '8px 16px', borderRadius: 8, border: `1px solid ${card.color}66`,
                background: card.color + '14', color: card.color,
                cursor: 'pointer', fontWeight: 600, fontSize: '0.83rem',
                transition: 'all 0.15s', alignSelf: 'flex-start',
              }}
            >
              {card.action} →
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN AdminPanel
// ─────────────────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'overview', label: '🏠 Overview' },
  { id: 'users', label: '👥 Users' },
  { id: 'pending', label: '⏳ Pending' },
  { id: 'alerts', label: '🚨 Alerts' },
  { id: 'logs', label: '📋 Login Logs' },
];

export default function AdminPanel() {
  const { isDarkMode } = useTheme();
  const [activeTab, setActiveTab] = useState('overview');
  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(true);

  const loadSummary = useCallback(async () => {
    setSummaryLoading(true);
    try {
      const res = await api.get('/admin/dashboard/summary');
      setSummary(res.data);
    } catch {
      setSummary(null);
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  useEffect(() => { loadSummary(); }, [loadSummary]);

  useEffect(() => {
    const handler = () => loadSummary();
    window.addEventListener('refresh', handler);
    return () => window.removeEventListener('refresh', handler);
  }, [loadSummary]);

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.6rem', fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.03em' }}>
              🛡️ Admin Control Centre
            </h1>
            <p style={{ margin: '4px 0 0', color: 'var(--text-muted)', fontSize: '0.88rem' }}>
              FraudGuard User management, security monitoring &amp; audit trails
            </p>
          </div>
          <button
            className="btn-secondary"
            onClick={loadSummary}
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
          >
            ↺ Refresh
          </button>
        </div>
      </div>

      {!summaryLoading && summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 14, marginBottom: 28 }}>
          <StatCard icon="👥" label="Total Users" value={summary.total_users} color="#60a5fa" />
          <StatCard icon="✅" label="Active Users" value={summary.active_users} color="#34d399" />
          <StatCard icon="⏳" label="Pending Approval" value={summary.pending_approvals} color="#fbbf24"
            sub={summary.pending_approvals > 0 ? 'Needs review' : 'All clear'} />
          <StatCard icon="🔒" label="Blocked" value={summary.blocked_users} color="#ef4444" />
          <StatCard icon="🔥" label="High Risk" value={summary.high_risk_users} color="#f97316"
            sub="Failed > 5× / hr" />
          <StatCard icon="❌" label="Failed Logins" value={summary.failed_logins_24h} color="#a78bfa"
            sub="Last 24 hours" />
        </div>
      )}

      <div style={{
        display: 'flex', gap: 4, flexWrap: 'wrap',
        background: 'var(--card-bg)',
        border: '1px solid var(--border)',
        borderRadius: 12, padding: 6, marginBottom: 20,
      }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            style={{
              flex: '1 1 auto', minWidth: 90, padding: '9px 16px',
              borderRadius: 9, border: 'none', cursor: 'pointer',
              fontWeight: 600, fontSize: '0.83rem',
              background: activeTab === t.id ? 'var(--purple, #7c3aed)' : 'transparent',
              color: activeTab === t.id ? '#fff' : 'var(--text-muted)',
              transition: 'all 0.15s',
              whiteSpace: 'nowrap',
            }}
          >
            {t.label}
            {t.id === 'pending' && summary?.pending_approvals > 0 && (
              <span style={{
                marginLeft: 6, background: '#fbbf24', color: '#000',
                borderRadius: 10, padding: '1px 7px', fontSize: '0.68rem', fontWeight: 800,
              }}>
                {summary.pending_approvals}
              </span>
            )}
            {t.id === 'alerts' && summary?.high_risk_users > 0 && (
              <span style={{
                marginLeft: 6, background: '#ef4444', color: '#fff',
                borderRadius: 10, padding: '1px 7px', fontSize: '0.68rem', fontWeight: 800,
              }}>
                {summary.high_risk_users}
              </span>
            )}
          </button>
        ))}
      </div>

      <div style={{
        background: 'var(--card-bg)',
        border: '1px solid var(--border)',
        borderRadius: 14, padding: '1.5rem',
      }}>
        {activeTab === 'overview' && <OverviewTab summary={summary} onNavigate={setActiveTab} />}
        {activeTab === 'users' && <UsersTable onRefreshSummary={loadSummary} />}
        {activeTab === 'pending' && <PendingTab onRefreshSummary={loadSummary} />}
        {activeTab === 'alerts' && <AlertsPanel onAck={loadSummary} />}
        {activeTab === 'logs' && <LoginLogsTab />}
      </div>
    </div>
  );
}
