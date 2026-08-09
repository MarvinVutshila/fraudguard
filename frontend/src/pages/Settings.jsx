import { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faUser, faCog, faLock, faKey, faRobot, faSave, faPlus, faTrash,
  faCheckCircle, faTimesCircle, faQrcode, faMoon, faSun, faEnvelope,
  faBell, faPlay, faStop, faSyncAlt, faChartLine, faTimes
} from '@fortawesome/free-solid-svg-icons';
import api from '../services/api';
import StatusBadge from '../components/StatusBadge';
import '../styles/settings.css';
import { API_BASE_URL } from '../services/api';
import { useTheme } from '../context/ThemeContext';

export default function Settings() {
  const { isDarkMode } = useTheme();
  const [activeTab, setActiveTab] = useState('profile');
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState(null);
  const [prefs, setPrefs] = useState({ theme: 'dark', notifications: { email: true, in_app: true }, language: 'en' });
  const [passwordData, setPasswordData] = useState({ currentPassword: '', newPassword: '' });
  const [apiKeys, setApiKeys] = useState([]);
  const [newKeyName, setNewKeyName] = useState('');
  const [systemSettings, setSystemSettings] = useState({});
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState('success');
  const [showModal, setShowModal] = useState(false);
  const [secret, setSecret] = useState('');
  const [code, setCode] = useState('');
  const [twofaLoading, setTwofaLoading] = useState(false);
  const [username, setUsername] = useState('user');
  const [qrUrl, setQrUrl] = useState('');
  const [agentConfig, setAgentConfig] = useState({
    enabled: false,
    model: 'xgboost',
    monitoringInterval: 60,
    autoRetrain: false,
    retrainSchedule: '0 2 * * *',
    alertThreshold: 0.85
  });

  const getToken = () => localStorage.getItem('fg_token');

  const showMessage = (text, type = 'success') => {
    setMessage(text);
    setMessageType(type);
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const res = await api.get('/settings/');
      setSettings(res.data);
      setPrefs(res.data.user?.preferences || { theme: 'dark', notifications: { email: true, in_app: true }, language: 'en' });
      const defaults = {
        approve_threshold: 0.2,
        block_threshold: 0.85,
        auto_retrain_enabled: false,
        alert_email: '',
        monitoring_interval: 60,
        auto_retrain_schedule: '0 2 * * *'
      };
      setSystemSettings({ ...defaults, ...(res.data.system || {}) });
      if (res.data.system?.agent_config) {
        setAgentConfig(prev => ({ ...prev, ...res.data.system.agent_config }));
      }
    } catch (err) {
      console.error('Failed to fetch settings:', err);
      showMessage('Failed to load settings', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchApiKeys = async () => {
    try {
      const res = await api.get('/settings/api-keys');
      setApiKeys(res.data);
    } catch (err) {
      console.error('Failed to fetch API keys:', err);
    }
  };

  useEffect(() => {
    fetchSettings();
    fetchApiKeys();
  }, []);

  // ---- Profile ----
  const updatePreferences = async () => {
    try {
      await api.put('/settings/preferences', prefs);
      showMessage('Preferences updated');
    } catch (err) {
      showMessage('Failed to update preferences', 'error');
    }
  };

  // ---- Security ----
  const changePassword = async () => {
    try {
      await api.post('/settings/change-password', {
        current_password: passwordData.currentPassword,
        new_password: passwordData.newPassword
      });
      showMessage('Password changed successfully');
      setPasswordData({ currentPassword: '', newPassword: '' });
    } catch (err) {
      showMessage(err.response?.data?.detail || 'Failed to change password', 'error');
    }
  };

  // ---- 2FA ----
  const start2faSetup = async () => {
    const token = getToken();
    if (!token || token.split('.').length !== 3) {
      showMessage('Session expired. Please log in again.', 'error');
      localStorage.clear();
      window.location.href = '/login';
      return;
    }
    setTwofaLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/settings/2fa/setup`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Setup failed');
      setSecret(data.secret);
      const user = JSON.parse(localStorage.getItem('user') || '{"username":"user"}');
      setUsername(user.username || 'user');
      const qr = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(`otpauth://totp/FraudGuard:${user.username}?secret=${data.secret}&issuer=FraudGuard`)}`;
      setQrUrl(qr);
      setShowModal(true);
    } catch (err) {
      showMessage('Error: ' + err.message, 'error');
    } finally {
      setTwofaLoading(false);
    }
  };

  const verify2fa = async () => {
    if (!code) return;
    setTwofaLoading(true);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/settings/2fa/verify-setup`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      });
      if (!res.ok) throw new Error('Invalid code');
      showMessage('2FA enabled successfully!');
      setShowModal(false);
      setCode('');
      fetchSettings();
    } catch (err) {
      showMessage('Verification failed: ' + err.message, 'error');
    } finally {
      setTwofaLoading(false);
    }
  };

  const disable2fa = async () => {
    const code = prompt('Enter your 2FA code to disable:');
    if (!code) return;
    try {
      await api.post('/settings/2fa/disable', { code });
      showMessage('2FA disabled successfully');
      fetchSettings();
    } catch (err) {
      showMessage(err.response?.data?.detail || 'Failed to disable 2FA', 'error');
    }
  };

  const closeModal = () => {
    setShowModal(false);
    setCode('');
    setTwofaLoading(false);
  };

  // ---- API Keys ----
  const createApiKey = async () => {
    if (!newKeyName.trim()) return;
    try {
      const res = await api.post('/settings/api-keys', { name: newKeyName });
      setApiKeys([res.data, ...apiKeys]);
      setNewKeyName('');
      showMessage('API key created: ' + res.data.key);
    } catch (err) {
      showMessage('Failed to create API key', 'error');
    }
  };

  const revokeApiKey = async (id) => {
    if (!window.confirm('Revoke this API key?')) return;
    try {
      await api.delete(`/settings/api-keys/${id}`);
      setApiKeys(apiKeys.filter(k => k.id !== id));
      showMessage('API key revoked');
    } catch (err) {
      showMessage('Failed to revoke API key', 'error');
    }
  };

  // ---- System Settings ----
  const updateSystemSetting = async (key, value) => {
    try {
      await api.put('/settings/system', { [key]: value });
      setSystemSettings({ ...systemSettings, [key]: value });
      showMessage('System setting updated');
    } catch (err) {
      showMessage('Failed to update system setting', 'error');
    }
  };

  // ---- Agent Config ----
  const updateAgentConfig = async (key, value) => {
    const newConfig = { ...agentConfig, [key]: value };
    setAgentConfig(newConfig);
    try {
      await api.put('/settings/system', { agent_config: newConfig });
      showMessage('Agent configuration saved');
    } catch (err) {
      showMessage('Failed to save agent config', 'error');
    }
  };

  if (loading) return <div className="settings-loading">Loading settings...</div>;

  return (
    <div className="settings-container">
      <h1 className="settings-header">⚙️ Settings</h1>
      {message && (
        <div className={`settings-message ${messageType}`}>
          {message}
        </div>
      )}

      <div className="settings-tabs">
        {[
          { id: 'profile', icon: faUser, label: 'Profile' },
          { id: 'security', icon: faLock, label: 'Security' },
          { id: 'api-keys', icon: faKey, label: 'API Keys' },
          { id: 'system', icon: faCog, label: 'System', admin: true },
          { id: 'agent', icon: faRobot, label: 'Agent AI', admin: true },
        ].map(tab => (
          <button
            key={tab.id}
            className={`settings-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
            disabled={tab.admin && settings?.user?.role !== 'admin'}
          >
            <FontAwesomeIcon icon={tab.icon} /> {tab.label}
          </button>
        ))}
      </div>

      <div className="settings-content">
        {/* ─── PROFILE TAB ─── */}
        {activeTab === 'profile' && (
          <div className="settings-section">
            <h3>Profile & Preferences</h3>
            <div className="settings-field">
              <label>Username</label>
              <span>{settings?.user?.username}</span>
            </div>
            <div className="settings-field">
              <label>Role</label>
              <span><StatusBadge status={settings?.user?.role} /></span>
            </div>
            <div className="settings-field">
              <label>Notifications</label>
              <div className="settings-checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={prefs.notifications?.email}
                    onChange={() => setPrefs({
                      ...prefs,
                      notifications: { ...prefs.notifications, email: !prefs.notifications?.email }
                    })}
                  />
                  <FontAwesomeIcon icon={faEnvelope} /> Email
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={prefs.notifications?.in_app}
                    onChange={() => setPrefs({
                      ...prefs,
                      notifications: { ...prefs.notifications, in_app: !prefs.notifications?.in_app }
                    })}
                  />
                  <FontAwesomeIcon icon={faBell} /> In‑App
                </label>
              </div>
            </div>
            <button className="btn-primary" onClick={updatePreferences}>
              <FontAwesomeIcon icon={faSave} /> Save Preferences
            </button>
            <p className="settings-hint" style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Theme switching is available in the top‑right corner.
            </p>
          </div>
        )}

        {/* ─── SECURITY TAB ─── */}
        {activeTab === 'security' && (
          <div className="settings-section">
            <h3>Security</h3>
            <div className="settings-field">
              <label>Two‑Factor Authentication</label>
              <div className="settings-2fa-status">
                {settings?.user?.totp_enabled ? (
                  <>
                    <span className="text-success"><FontAwesomeIcon icon={faCheckCircle} /> Enabled</span>
                    <button className="btn-secondary" onClick={disable2fa}>
                      <FontAwesomeIcon icon={faTimesCircle} /> Disable
                    </button>
                  </>
                ) : (
                  <>
                    <span className="text-muted"><FontAwesomeIcon icon={faTimesCircle} /> Disabled</span>
                    <button className="btn-secondary" onClick={start2faSetup} disabled={twofaLoading}>
                      <FontAwesomeIcon icon={faQrcode} /> {twofaLoading ? 'Loading...' : 'Setup'}
                    </button>
                  </>
                )}
              </div>
            </div>

            <div className="settings-field">
              <label>Change Password</label>
              <div className="settings-password-form">
                <input
                  type="password"
                  placeholder="Current password"
                  value={passwordData.currentPassword}
                  onChange={(e) => setPasswordData({ ...passwordData, currentPassword: e.target.value })}
                />
                <input
                  type="password"
                  placeholder="New password"
                  value={passwordData.newPassword}
                  onChange={(e) => setPasswordData({ ...passwordData, newPassword: e.target.value })}
                />
                <button className="btn-primary" onClick={changePassword}>
                  <FontAwesomeIcon icon={faLock} /> Change Password
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ─── API KEYS TAB ─── */}
        {activeTab === 'api-keys' && (
          <div className="settings-section">
            <h3>API Keys</h3>
            <div className="settings-api-key-create">
              <input
                type="text"
                placeholder="Key name"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
              />
              <button className="btn-primary" onClick={createApiKey}>
                <FontAwesomeIcon icon={faPlus} /> Generate Key
              </button>
            </div>
            <div className="settings-api-keys-list">
              {apiKeys.length === 0 ? (
                <p>No API keys created.</p>
              ) : (
                apiKeys.map(key => (
                  <div key={key.id} className="settings-api-key-item">
                    <div>
                      <strong>{key.name}</strong>
                      <span className="settings-api-key-prefix">Prefix: {key.prefix}</span>
                      <span className="settings-api-key-status">
                        {key.revoked ? (
                          <span className="text-danger">Revoked</span>
                        ) : (
                          <span className="text-success">Active</span>
                        )}
                      </span>
                      <span className="settings-api-key-expires">Expires: {new Date(key.expires_at).toLocaleDateString()}</span>
                    </div>
                    {!key.revoked && (
                      <button className="btn-danger" onClick={() => revokeApiKey(key.id)}>
                        <FontAwesomeIcon icon={faTrash} /> Revoke
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* ─── SYSTEM TAB ─── */}
        {activeTab === 'system' && settings?.user?.role === 'admin' && (
          <div className="settings-section">
            <h3>System Configuration</h3>
            <div className="settings-field">
              <label>Approve Threshold</label>
              <input
                type="number"
                step="0.01"
                value={systemSettings.approve_threshold || 0.2}
                onChange={(e) => updateSystemSetting('approve_threshold', parseFloat(e.target.value))}
              />
              <span className="hint">Transactions with risk below this threshold are approved.</span>
            </div>
            <div className="settings-field">
              <label>Block Threshold</label>
              <input
                type="number"
                step="0.01"
                value={systemSettings.block_threshold || 0.85}
                onChange={(e) => updateSystemSetting('block_threshold', parseFloat(e.target.value))}
              />
              <span className="hint">Transactions with risk above this threshold are blocked.</span>
            </div>
            <div className="settings-field">
              <label>Auto‑retrain Enabled</label>
              <input
                type="checkbox"
                checked={systemSettings.auto_retrain_enabled || false}
                onChange={(e) => updateSystemSetting('auto_retrain_enabled', e.target.checked)}
              />
            </div>
            <div className="settings-field">
              <label>Alert Email</label>
              <input
                type="email"
                value={systemSettings.alert_email || ''}
                onChange={(e) => updateSystemSetting('alert_email', e.target.value)}
              />
            </div>
          </div>
        )}

        {/* ─── AGENT AI TAB ─── */}
        {activeTab === 'agent' && settings?.user?.role === 'admin' && (
          <div className="settings-section">
            <h3>AI Agent Configuration</h3>
            <div className="settings-field">
              <label>Agent Status</label>
              <div className="settings-radio-group">
                <label className="settings-radio">
                  <input
                    type="radio"
                    name="agentStatus"
                    value="enabled"
                    checked={agentConfig.enabled === true}
                    onChange={() => updateAgentConfig('enabled', true)}
                  />
                  <FontAwesomeIcon icon={faPlay} style={{ color: '#10b981' }} /> Active
                </label>
                <label className="settings-radio">
                  <input
                    type="radio"
                    name="agentStatus"
                    value="disabled"
                    checked={agentConfig.enabled === false}
                    onChange={() => updateAgentConfig('enabled', false)}
                  />
                  <FontAwesomeIcon icon={faStop} style={{ color: '#ef4444' }} /> Inactive
                </label>
              </div>
            </div>

            <div className="settings-field">
              <label>Model</label>
              <select
                value={agentConfig.model || 'xgboost'}
                onChange={(e) => updateAgentConfig('model', e.target.value)}
                className="settings-select"
              >
                <option value="xgboost">XGBoost</option>
                <option value="random_forest">Random Forest</option>
                <option value="neural_network">Neural Network</option>
                <option value="ensemble">Ensemble</option>
              </select>
            </div>

            <div className="settings-field">
              <label>Monitoring Interval (seconds)</label>
              <input
                type="number"
                value={agentConfig.monitoringInterval || 60}
                onChange={(e) => updateAgentConfig('monitoringInterval', parseInt(e.target.value) || 60)}
              />
              <span className="hint">How often the agent checks for new data.</span>
            </div>

            <div className="settings-field">
              <label>Auto‑retrain</label>
              <div className="settings-checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={agentConfig.autoRetrain || false}
                    onChange={(e) => updateAgentConfig('autoRetrain', e.target.checked)}
                  />
                  <FontAwesomeIcon icon={faSyncAlt} /> Enable automatic retraining
                </label>
              </div>
            </div>

            {agentConfig.autoRetrain && (
              <div className="settings-field">
                <label>Retrain Schedule (cron)</label>
                <input
                  type="text"
                  placeholder="0 2 * * *"
                  value={agentConfig.retrainSchedule || '0 2 * * *'}
                  onChange={(e) => updateAgentConfig('retrainSchedule', e.target.value)}
                />
                <span className="hint">Cron expression for retraining (e.g., daily at 2 AM).</span>
              </div>
            )}

            <div className="settings-field">
              <label>Alert Threshold</label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={agentConfig.alertThreshold || 0.85}
                onChange={(e) => updateAgentConfig('alertThreshold', parseFloat(e.target.value) || 0.85)}
              />
              <span className="hint">Probability above which the agent triggers alerts.</span>
            </div>

            <div className="settings-field" style={{ marginTop: '1rem' }}>
              <button className="btn-primary" onClick={() => alert('Agent run triggered manually.')}>
                <FontAwesomeIcon icon={faChartLine} /> Run Agent Now
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ─── 2FA MODAL ─── (theme‑aware) */}
      {showModal && (
        <div
          className="modal-overlay open"
          onClick={closeModal}
          style={{
            position: 'fixed',
            top: 0, left: 0, right: 0, bottom: 0,
            background: isDarkMode ? 'rgba(0,0,0,0.85)' : 'rgba(0,0,0,0.6)',
            backdropFilter: 'blur(6px)',
            zIndex: 99999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem'
          }}
        >
          <div
            className="modal-card"
            onClick={(e) => e.stopPropagation()}
            style={{
              background: isDarkMode ? '#1e1e2f' : '#ffffff',
              padding: '2rem',
              borderRadius: '16px',
              maxWidth: '450px',
              width: '100%',
              border: isDarkMode ? '1px solid #2d2d44' : '1px solid #ddd',
              boxShadow: '0 10px 40px rgba(0,0,0,0.3)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, color: isDarkMode ? '#fff' : '#1a1a2e' }}>2FA Setup</h3>
              <button
                onClick={closeModal}
                style={{
                  background: 'none',
                  border: 'none',
                  color: isDarkMode ? '#aaa' : '#666',
                  fontSize: '1.2rem',
                  cursor: 'pointer'
                }}
              >
                <FontAwesomeIcon icon={faTimes} />
              </button>
            </div>

            <p style={{ color: isDarkMode ? '#ccc' : '#555' }}>Scan this QR code with your authenticator app:</p>

            <div style={{
              display: 'flex',
              justifyContent: 'center',
              padding: '1rem',
              background: isDarkMode ? '#0b0f1c' : '#f8f9fa',
              borderRadius: '8px',
              margin: '1rem 0'
            }}>
              {qrUrl ? (
                <img
                  src={qrUrl}
                  alt="QR Code"
                  style={{ width: '200px', height: '200px' }}
                  onError={(e) => {
                    console.error('❌ QR image failed to load');
                    e.target.style.display = 'none';
                    document.getElementById('secret-fallback').style.display = 'block';
                  }}
                />
              ) : (
                <p style={{ color: 'red' }}>No QR URL set</p>
              )}
              <div id="secret-fallback" style={{ display: 'none', color: isDarkMode ? '#fff' : '#1a1a2e' }}>
                <p>QR generation failed. Enter secret manually:</p>
                <code style={{ background: isDarkMode ? '#2d2d44' : '#e9ecef', padding: '0.3rem 0.6rem', borderRadius: '4px' }}>{secret}</code>
              </div>
            </div>

            <p style={{ color: isDarkMode ? '#888' : '#666', fontSize: '0.9rem' }}>
              Or enter this secret manually: <code style={{
                background: isDarkMode ? '#2d2d44' : '#e9ecef',
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                color: isDarkMode ? '#fff' : '#1a1a2e'
              }}>{secret}</code>
            </p>

            <div style={{ marginTop: '1rem' }}>
              <label style={{ color: isDarkMode ? '#ccc' : '#555', display: 'block', marginBottom: '0.3rem' }}>
                Enter 6-digit code
              </label>
              <input
                type="text"
                maxLength="6"
                placeholder="123456"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  background: isDarkMode ? '#14141e' : '#ffffff',
                  border: isDarkMode ? '1px solid #2d2d44' : '1px solid #ccc',
                  borderRadius: '6px',
                  color: isDarkMode ? '#fff' : '#1a1a2e',
                  fontSize: '1rem'
                }}
              />
            </div>

            <button
              onClick={verify2fa}
              disabled={twofaLoading || !code}
              style={{
                width: '100%',
                padding: '0.7rem',
                marginTop: '1rem',
                background: code ? '#10b981' : '#374151',
                border: 'none',
                borderRadius: '6px',
                color: '#fff',
                fontWeight: '600',
                cursor: code ? 'pointer' : 'not-allowed'
              }}
            >
              {twofaLoading ? 'Verifying...' : 'Verify & Enable'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}