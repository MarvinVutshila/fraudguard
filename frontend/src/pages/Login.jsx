import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_BASE_URL } from '../services/api';

export default function Login() {
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const [twofaRequired, setTwofaRequired] = useState(false);
  const [twofaCode, setTwofaCode] = useState('');
  const [tempToken, setTempToken] = useState('');
  const [twofaLoading, setTwofaLoading] = useState(false);

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
      if (!response.ok) throw new Error(data.detail || 'Login failed');
      if (data.requires_2fa) {
        setTempToken(data.temp_token);
        setTwofaRequired(true);
        setLoading(false);
        return;
      }
      localStorage.setItem('fg_token', data.access_token);
      if (data.refresh_token) localStorage.setItem('fg_refresh_token', data.refresh_token);
      localStorage.setItem('fg_role', data.role || 'analyst');
      navigate('/');
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  // ---- 2FA ----
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
      if (!response.ok) throw new Error(data.detail || 'Verification failed');
      localStorage.setItem('fg_token', data.access_token);
      if (data.refresh_token) localStorage.setItem('fg_refresh_token', data.refresh_token);
      localStorage.setItem('fg_role', data.role || 'analyst');
      navigate('/');
    } catch (err) {
      setError(err.message);
    } finally {
      setTwofaLoading(false);
    }
  };

  // ---- Signup ----
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
      if (!response.ok) throw new Error(data.detail || 'Registration failed');
      setShowSignup(false);
      alert('Account created! Please wait for admin approval.');
      setSignupEmail('');
      setSignupPassword('');
      setSignupConfirm('');
      setSignupAvatar(null);
    } catch (err) {
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
    <div className="login-page" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem', background: 'var(--bg)' }}>
      <div className="login-container" style={{ display: 'flex', maxWidth: '1100px', width: '100%', background: 'var(--surface)', borderRadius: '20px', overflow: 'hidden', boxShadow: 'var(--shadow)', flexDirection: window.innerWidth < 768 ? 'column' : 'row' }}>

        {/* ---- Left Panel (hidden on mobile) ---- */}
        <div className="login-left" style={{
          flex: '1.2', padding: '3rem 2.5rem',
          background: 'linear-gradient(145deg, rgba(11,15,28,0.92), rgba(11,15,28,0.8)), url(/Marvin.jpg) center/cover no-repeat',
          display: window.innerWidth < 768 ? 'none' : 'flex',
          flexDirection: 'column', justifyContent: 'center', color: '#fff'
        }}>
          <div className="brand-block" style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
            <div style={{ fontSize: '2.5rem' }}>🛡️</div>
            <div>
              <h1 style={{ fontFamily: 'var(--display)', fontSize: '2rem', margin: 0, fontWeight: 700 }}>FraudGuard</h1>
              <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', opacity: 0.6, letterSpacing: '0.1em' }}>Banking Intelligence Platform</span>
            </div>
          </div>
          <div style={{ marginTop: '3rem' }}>
            <h2 style={{ fontSize: 'clamp(2rem, 4vw, 2.8rem)', fontWeight: 700, lineHeight: 1.1 }}>
              Real‑time fraud<br /><span style={{ color: '#06b6d4' }}>detection at scale.</span>
            </h2>
            <p style={{ maxWidth: '400px', opacity: 0.8, lineHeight: 1.6, marginTop: '0.5rem' }}>
              Monitor every transaction, flag suspicious activity with XGBoost ML, and route borderline cases to human analysts.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '2rem', marginTop: '2rem' }}>
            <div><span style={{ display: 'block', fontSize: '1.8rem', fontWeight: 700, color: '#06b6d4' }}>99.8%</span><label style={{ fontSize: '0.6rem', textTransform: 'uppercase', opacity: 0.6 }}>Accuracy</label></div>
            <div><span style={{ display: 'block', fontSize: '1.8rem', fontWeight: 700, color: '#06b6d4' }}>&lt;50ms</span><label style={{ fontSize: '0.6rem', textTransform: 'uppercase', opacity: 0.6 }}>Latency</label></div>
            <div><span style={{ display: 'block', fontSize: '1.8rem', fontWeight: 700, color: '#06b6d4' }}>24/7</span><label style={{ fontSize: '0.6rem', textTransform: 'uppercase', opacity: 0.6 }}>Monitoring</label></div>
          </div>
          <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.7rem', opacity: 0.6, marginTop: '1rem' }}>
            <span>🔒 SOC 2 Type II</span>
            <span>💳 PCI‑DSS</span>
            <span>🔐 AES‑256</span>
          </div>
        </div>

        {/* ---- Right Panel (login form) ---- */}
        <div className="login-right" style={{ flex: 1, padding: '2rem', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--surface)' }}>
          <div style={{ width: '100%', maxWidth: '400px' }}>

            {/* Avatar – now theme‑aware */}
            <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
              <div style={{
                width: '80px', height: '80px', borderRadius: '50%',
                margin: '0 auto 0.5rem',
                padding: '3px',
                background: 'linear-gradient(135deg, var(--accent), var(--cyan))',
                border: '2px solid var(--surface)',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              }}>
                <img
                  src="/Marvin.jpg"
                  alt="avatar"
                  style={{
                    width: '100%', height: '100%',
                    borderRadius: '50%',
                    objectFit: 'cover',
                    border: '3px solid var(--surface)',
                    background: 'var(--surface)', // ensures fallback color
                  }}
                />
              </div>
              <div style={{ fontFamily: 'var(--display)', fontSize: '1.1rem', fontWeight: 600 }}>Welcome Back</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Fraud Analyst</div>
            </div>

            {!twofaRequired ? (
              <>
                <h2 style={{ fontFamily: 'var(--display)', fontSize: '1.6rem', marginBottom: '0.1rem' }}>Sign In</h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>Access your monitoring dashboard</p>
                <form onSubmit={handleLogin}>
                  <div className="field" style={{ marginBottom: '1.2rem' }}>
                    <label style={{ display: 'block', fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>Email Address</label>
                    <div style={{ position: 'relative' }}>
                      <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-faint)' }}>✉️</span>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="analyst@bank.com"
                        required
                        disabled={loading}
                        style={{
                          width: '100%',
                          padding: '0.75rem 0.9rem 0.75rem 2.8rem',
                          background: 'var(--surface2)',
                          border: '1px solid var(--border-md)',
                          borderRadius: '12px',
                          color: 'var(--text)',
                          fontSize: '0.9rem',
                          minHeight: '48px',
                          transition: 'border-color 0.2s, box-shadow 0.2s'
                        }}
                      />
                    </div>
                  </div>
                  <div className="field" style={{ marginBottom: '1.2rem' }}>
                    <label style={{ display: 'block', fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>Password</label>
                    <div style={{ position: 'relative' }}>
                      <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-faint)' }}>🔒</span>
                      <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        required
                        disabled={loading}
                        style={{
                          width: '100%',
                          padding: '0.75rem 0.9rem 0.75rem 2.8rem',
                          background: 'var(--surface2)',
                          border: '1px solid var(--border-md)',
                          borderRadius: '12px',
                          color: 'var(--text)',
                          fontSize: '0.9rem',
                          minHeight: '48px'
                        }}
                      />
                    </div>
                  </div>
                  {error && (
                    <div style={{
                      padding: '0.5rem 0.8rem',
                      background: 'rgba(239,68,68,0.08)',
                      border: '1px solid rgba(239,68,68,0.2)',
                      borderRadius: '8px',
                      marginBottom: '0.8rem',
                      color: '#fca5a5',
                      fontSize: '0.8rem'
                    }}>
                      {error}
                    </div>
                  )}
                  <button
                    type="submit"
                    className="btn-login"
                    disabled={loading}
                    style={{
                      width: '100%',
                      padding: '0.85rem',
                      background: 'linear-gradient(135deg, var(--accent), #1d4ed8)',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '12px',
                      fontWeight: 600,
                      fontSize: '0.95rem',
                      cursor: 'pointer',
                      minHeight: '48px',
                      transition: 'opacity 0.2s'
                    }}
                  >
                    {loading ? 'Signing in…' : 'Sign In →'}
                  </button>
                </form>
                <div style={{ textAlign: 'center', marginTop: '1.2rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Don't have an account?{' '}
                  <button type="button" className="link-btn" onClick={() => setShowSignup(true)} style={{ background: 'none', border: 'none', color: 'var(--cyan)', cursor: 'pointer', textDecoration: 'underline', fontWeight: 500 }}>
                    Create new account
                  </button>
                </div>
              </>
            ) : (
              // 2FA step
              <>
                <h2 style={{ fontFamily: 'var(--display)', fontSize: '1.6rem', marginBottom: '0.1rem' }}>Two‑Factor Authentication</h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>Enter the 6‑digit code from your authenticator app</p>
                <form onSubmit={handleTwofaSubmit}>
                  <div className="field" style={{ marginBottom: '1.2rem' }}>
                    <label style={{ display: 'block', fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>Verification Code</label>
                    <div style={{ position: 'relative' }}>
                      <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-faint)' }}>🔐</span>
                      <input
                        type="text"
                        maxLength="6"
                        placeholder="123456"
                        value={twofaCode}
                        onChange={(e) => setTwofaCode(e.target.value.replace(/\D/g, ''))}
                        required
                        disabled={twofaLoading}
                        style={{
                          width: '100%',
                          padding: '0.75rem 0.9rem 0.75rem 2.8rem',
                          background: 'var(--surface2)',
                          border: '1px solid var(--border-md)',
                          borderRadius: '12px',
                          color: 'var(--text)',
                          fontSize: '0.9rem',
                          minHeight: '48px'
                        }}
                      />
                    </div>
                  </div>
                  {error && (
                    <div style={{
                      padding: '0.5rem 0.8rem',
                      background: 'rgba(239,68,68,0.08)',
                      border: '1px solid rgba(239,68,68,0.2)',
                      borderRadius: '8px',
                      marginBottom: '0.8rem',
                      color: '#fca5a5',
                      fontSize: '0.8rem'
                    }}>
                      {error}
                    </div>
                  )}
                  <button
                    type="submit"
                    className="btn-login"
                    disabled={twofaLoading}
                    style={{
                      width: '100%',
                      padding: '0.85rem',
                      background: 'linear-gradient(135deg, var(--accent), #1d4ed8)',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '12px',
                      fontWeight: 600,
                      fontSize: '0.95rem',
                      cursor: 'pointer',
                      minHeight: '48px'
                    }}
                  >
                    {twofaLoading ? 'Verifying…' : 'Verify →'}
                  </button>
                </form>
                <div style={{ marginTop: '0.5rem' }}>
                  <button
                    type="button"
                    className="link-btn"
                    onClick={() => { setTwofaRequired(false); setError(''); setTwofaCode(''); }}
                    style={{ background: 'none', border: 'none', color: 'var(--cyan)', cursor: 'pointer', fontSize: '0.8rem', textDecoration: 'underline' }}
                  >
                    ← Back to login
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ---- Signup Modal (unchanged, but can be improved) ---- */}
      {showSignup && (
        <div className="modal-overlay open" onClick={() => setShowSignup(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(7px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1rem' }}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ background: 'var(--surface)', border: '1px solid var(--border-md)', borderRadius: 'var(--radius-lg)', width: '500px', maxWidth: '95vw', transform: 'translateY(0)', maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="modal-hdr" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1.2rem 1.4rem', borderBottom: '1px solid var(--border)' }}>
              <h3 style={{ fontFamily: 'var(--display)', fontSize: '1rem', fontWeight: 700 }}>Create Account</h3>
              <button className="modal-close" onClick={() => setShowSignup(false)} style={{ cursor: 'pointer', background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '1.1rem' }}>✕</button>
            </div>
            <div className="modal-body" style={{ padding: '1.3rem 1.4rem' }}>
              {signupError && (
                <div style={{
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
              <div className="field" style={{ marginBottom: '1.2rem' }}>
                <label style={{ display: 'block', fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>Email Address</label>
                <input
                  type="email"
                  value={signupEmail}
                  onChange={(e) => setSignupEmail(e.target.value)}
                  placeholder="you@bank.com"
                  disabled={signupLoading}
                  style={{
                    width: '100%',
                    padding: '0.5rem 0.7rem',
                    background: 'var(--surface2)',
                    border: '1px solid var(--border-md)',
                    borderRadius: '8px',
                    color: 'var(--text)',
                    fontSize: '0.9rem',
                    minHeight: '44px'
                  }}
                />
              </div>
              <div className="field" style={{ marginBottom: '1.2rem' }}>
                <label style={{ display: 'block', fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>Password</label>
                <input
                  type="password"
                  value={signupPassword}
                  onChange={(e) => setSignupPassword(e.target.value)}
                  placeholder="••••••••"
                  disabled={signupLoading}
                  style={{
                    width: '100%',
                    padding: '0.5rem 0.7rem',
                    background: 'var(--surface2)',
                    border: '1px solid var(--border-md)',
                    borderRadius: '8px',
                    color: 'var(--text)',
                    fontSize: '0.9rem',
                    minHeight: '44px'
                  }}
                />
              </div>
              <div className="field" style={{ marginBottom: '1.2rem' }}>
                <label style={{ display: 'block', fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>Confirm Password</label>
                <input
                  type="password"
                  value={signupConfirm}
                  onChange={(e) => setSignupConfirm(e.target.value)}
                  placeholder="••••••••"
                  disabled={signupLoading}
                  style={{
                    width: '100%',
                    padding: '0.5rem 0.7rem',
                    background: 'var(--surface2)',
                    border: '1px solid var(--border-md)',
                    borderRadius: '8px',
                    color: 'var(--text)',
                    fontSize: '0.9rem',
                    minHeight: '44px'
                  }}
                />
              </div>
              <div className="field signup-avatar" style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>Profile Picture (optional)</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleAvatarUpload}
                  disabled={signupLoading}
                  style={{ padding: '0.4rem 0', background: 'var(--surface2)', border: '1px solid var(--border-md)', borderRadius: '8px', width: '100%' }}
                />
                {signupAvatar && (
                  <div style={{ marginTop: '0.5rem' }}>
                    <img src={signupAvatar} alt="avatar preview" style={{ width: '60px', height: '60px', borderRadius: '50%', objectFit: 'cover', border: '2px solid var(--border)' }} />
                  </div>
                )}
              </div>
            </div>
            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.7rem', padding: '1rem 1.4rem', borderTop: '1px solid var(--border)' }}>
              <button className="btn-secondary" onClick={() => setShowSignup(false)} disabled={signupLoading} style={{ padding: '0.48rem 1rem', background: 'var(--surface2)', border: '1px solid var(--border-md)', borderRadius: 'var(--radius)', color: 'var(--text-muted)', cursor: 'pointer' }}>Cancel</button>
              <button className="btn-primary" onClick={handleSignup} disabled={signupLoading} style={{ padding: '0.48rem 1rem', background: 'linear-gradient(135deg, var(--accent), #1d4ed8)', color: '#fff', border: 'none', borderRadius: 'var(--radius)', fontWeight: 600, cursor: 'pointer' }}>{signupLoading ? 'Creating…' : 'Create Account'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}