import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_BASE_URL } from '../services/api';   // <-- IMPORT from api.js

export default function Login() {
  const navigate = useNavigate();

  // Login form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // 2FA state
  const [twofaRequired, setTwofaRequired] = useState(false);
  const [twofaCode, setTwofaCode] = useState('');
  const [tempToken, setTempToken] = useState('');
  const [twofaLoading, setTwofaLoading] = useState(false);

  // Signup modal state
  const [showSignup, setShowSignup] = useState(false);
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupConfirm, setSignupConfirm] = useState('');
  const [signupError, setSignupError] = useState('');
  const [signupLoading, setSignupLoading] = useState(false);
  const [signupAvatar, setSignupAvatar] = useState(null);

  // ---- Login ----
  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: email, password })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }
      
      if (data.requires_2fa) {
        setTempToken(data.temp_token);
        setTwofaRequired(true);
        setLoading(false);
        return;
      }
      
      localStorage.setItem('fg_token', data.access_token);
      if (data.refresh_token) {
        localStorage.setItem('fg_refresh_token', data.refresh_token);
      }
      localStorage.setItem('fg_role', data.role || 'analyst');
      
      navigate('/');
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  // ---- 2FA verification ----
  const handleTwofaSubmit = async (e) => {
    e.preventDefault();
    if (!twofaCode) return;
    setTwofaLoading(true);
    setError('');
    
    try {
      const response = await fetch(`${API_BASE_URL}/auth/2fa/verify-login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ temp_token: tempToken, code: twofaCode })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Verification failed');
      }
      
      localStorage.setItem('fg_token', data.access_token);
      if (data.refresh_token) {
        localStorage.setItem('fg_refresh_token', data.refresh_token);
      }
      localStorage.setItem('fg_role', data.role || 'analyst');
      
      navigate('/');
    } catch (err) {
      setError(err.message);
    } finally {
      setTwofaLoading(false);
    }
  };

  // ---- Signup handlers ----
  const handleSignup = async () => {
    if (!signupEmail || !signupPassword || signupPassword !== signupConfirm) {
      setSignupError('Please fill all fields and ensure passwords match.');
      return;
    }
    setSignupLoading(true);
    setSignupError('');
    try {
      const payload = {
        username: signupEmail,
        password: signupPassword,
        avatar_url: signupAvatar || null,
      };
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Registration failed');
      }
      setShowSignup(false);
      alert('Account created! Please wait for admin approval.');
      setSignupEmail('');
      setSignupPassword('');
      setSignupConfirm('');
      setSignupAvatar(null);
    } catch (err) {
      console.error('Signup error:', err);
      setSignupError(err.message || 'Registration failed');
    } finally {
      setSignupLoading(false);
    }
  };

  const handleAvatarUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => setSignupAvatar(ev.target.result);
    reader.readAsDataURL(file);
  };

  // ---- Render ----
  return (
    <div className="login-page">
      <div className="login-container">
        {/* Left panel – unchanged */}
        <div className="login-left">
          <div className="brand-block">
            <div className="brand-icon">🛡️</div>
            <div>
              <h1 className="brand-title">FraudGuard</h1>
              <span className="brand-tagline">Banking Intelligence Platform</span>
            </div>
          </div>
          <div className="hero-text" style={{ marginTop: '40px' }}>
            <h2>Real‑time fraud<br /><span>detection at scale.</span></h2>
            <p>Monitor every transaction, flag suspicious activity with XGBoost ML, and route borderline cases to human analysts.</p>
          </div>
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-number">99.8%</span>
              <label>Accuracy</label>
            </div>
            <div className="stat-item">
              <span className="stat-number">&lt;50ms</span>
              <label>Latency</label>
            </div>
            <div className="stat-item">
              <span className="stat-number">24/7</span>
              <label>Monitoring</label>
            </div>
          </div>
          <div className="trust-badges">
            <span>🔒 SOC 2 Type II</span>
            <span>💳 PCI‑DSS</span>
            <span>🔐 AES‑256</span>
          </div>
        </div>

        {/* Right panel */}
        <div className="login-right">
          <div className="login-card">
            <div className="card-avatar">
              <div className="avatar-ring">
                <img src="/Marvin.jpg" alt="avatar" />
              </div>
              <div className="avatar-name">Welcome Back</div>
              <div className="avatar-role">Fraud Analyst</div>
            </div>

            {!twofaRequired ? (
              <>
                <h2>Sign In</h2>
                <p className="card-sub">Access your monitoring dashboard</p>
                <form onSubmit={handleLogin}>
                  <div className="field">
                    <label>Email Address</label>
                    <div className="input-wrap">
                      <span className="input-icon">✉️</span>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="analyst@bank.com"
                        required
                        disabled={loading}
                      />
                    </div>
                  </div>
                  <div className="field">
                    <label>Password</label>
                    <div className="input-wrap">
                      <span className="input-icon">🔒</span>
                      <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        required
                        disabled={loading}
                      />
                    </div>
                  </div>
                  {error && (
                    <div className="error-message" style={{
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      padding: '12px 16px',
                      background: 'rgba(239,68,68,0.1)',
                      border: '1px solid rgba(239,68,68,0.3)',
                      borderRadius: '8px',
                      marginBottom: '12px',
                      color: '#fca5a5',
                      fontSize: '0.85rem',
                      lineHeight: '1.6'
                    }}>
                      {error}
                    </div>
                  )}
                  <button type="submit" className="btn-login" disabled={loading}>
                    {loading ? 'Signing in…' : 'Sign In →'}
                  </button>
                </form>
                <div className="signup-row">
                  Don't have an account?{' '}
                  <button type="button" className="link-btn" onClick={() => setShowSignup(true)}>
                    Create new account
                  </button>
                </div>
              </>
            ) : (
              // ---- 2FA step ----
              <>
                <h2>Two‑Factor Authentication</h2>
                <p className="card-sub">Enter the 6‑digit code from your authenticator app</p>
                <form onSubmit={handleTwofaSubmit}>
                  <div className="field">
                    <label>Verification Code</label>
                    <div className="input-wrap">
                      <span className="input-icon">🔐</span>
                      <input
                        type="text"
                        maxLength="6"
                        placeholder="123456"
                        value={twofaCode}
                        onChange={(e) => setTwofaCode(e.target.value.replace(/\D/g, ''))}
                        required
                        disabled={twofaLoading}
                      />
                    </div>
                  </div>
                  {error && (
                    <div className="error-message" style={{
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      padding: '12px 16px',
                      background: 'rgba(239,68,68,0.1)',
                      border: '1px solid rgba(239,68,68,0.3)',
                      borderRadius: '8px',
                      marginBottom: '12px',
                      color: '#fca5a5',
                      fontSize: '0.85rem',
                      lineHeight: '1.6'
                    }}>
                      {error}
                    </div>
                  )}
                  <button type="submit" className="btn-login" disabled={twofaLoading}>
                    {twofaLoading ? 'Verifying…' : 'Verify →'}
                  </button>
                </form>
                <div style={{ marginTop: '0.5rem' }}>
                  <button
                    type="button"
                    className="link-btn"
                    onClick={() => {
                      setTwofaRequired(false);
                      setError('');
                      setTwofaCode('');
                    }}
                    style={{ fontSize: '0.8rem' }}
                  >
                    ← Back to login
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Signup Modal */}
      {showSignup && (
        <div className="modal-overlay open" onClick={() => setShowSignup(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-hdr">
              <h3>Create Account</h3>
              <button className="modal-close" onClick={() => setShowSignup(false)}>✕</button>
            </div>
            <div className="modal-body">
              {signupError && (
                <div className="error-message" style={{
                  padding: '10px 14px',
                  background: 'rgba(239,68,68,0.1)',
                  border: '1px solid rgba(239,68,68,0.3)',
                  borderRadius: '8px',
                  marginBottom: '1rem',
                  color: '#fca5a5',
                  fontSize: '0.85rem'
                }}>
                  {signupError}
                </div>
              )}
              
              <div className="field">
                <label>Email Address</label>
                <input
                  type="email"
                  value={signupEmail}
                  onChange={(e) => setSignupEmail(e.target.value)}
                  placeholder="you@bank.com"
                  disabled={signupLoading}
                />
              </div>

              <div className="field">
                <label>Password</label>
                <input
                  type="password"
                  value={signupPassword}
                  onChange={(e) => setSignupPassword(e.target.value)}
                  placeholder="••••••••"
                  disabled={signupLoading}
                />
              </div>

              <div className="field">
                <label>Confirm Password</label>
                <input
                  type="password"
                  value={signupConfirm}
                  onChange={(e) => setSignupConfirm(e.target.value)}
                  placeholder="••••••••"
                  disabled={signupLoading}
                />
              </div>

              <div className="field signup-avatar">
                <label>Profile Picture (optional)</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleAvatarUpload}
                  disabled={signupLoading}
                  style={{ padding: '0.4rem 0' }}
                />
                {signupAvatar && (
                  <div style={{ marginTop: '0.5rem' }}>
                    <img src={signupAvatar} alt="avatar preview" style={{ width: '60px', height: '60px', borderRadius: '50%', objectFit: 'cover' }} />
                  </div>
                )}
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setShowSignup(false)} disabled={signupLoading}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleSignup} disabled={signupLoading}>
                {signupLoading ? 'Creating…' : 'Create Account'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}