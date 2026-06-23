import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // Signup modal state
  const [showSignup, setShowSignup] = useState(false);
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupConfirm, setSignupConfirm] = useState('');
  const [signupError, setSignupError] = useState('');
  const [signupLoading, setSignupLoading] = useState(false);
  const [signupAvatar, setSignupAvatar] = useState(null);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.post('/auth/login', { username: email, password });
      const { access_token } = res.data;
      localStorage.setItem('fg_token', access_token);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

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
      await api.post('/auth/register', payload);
      setShowSignup(false);
      alert('Account created! You can now log in.');
      setSignupEmail('');
      setSignupPassword('');
      setSignupConfirm('');
      setSignupAvatar(null);
    } catch (err) {
      setSignupError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setSignupLoading(false);
    }
  };

  const handleAvatarUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      setSignupAvatar(ev.target.result);
    };
    reader.readAsDataURL(file);
  };

  return (
    <div className="login-page">
      <div className="login-container">
        {/* Left panel - Brand & stats */}
        <div className="login-left">
          <div className="brand-block">
            <div className="brand-icon">🛡️</div>
            <div>
              <h1 className="brand-title">FraudGuard</h1>
              <span className="brand-tagline">Banking Intelligence Platform</span>
            </div>
          </div>
          
          {/* ✅ FIX: Added margin-top to push text down */}
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

        {/* Right panel - Login form */}
        <div className="login-right">
          <div className="login-card">
            <div className="card-avatar">
              <div className="avatar-ring">
                <img src="/Marvin.jpg" alt="avatar" />
              </div>
              <div className="avatar-name">Welcome Back</div>
              <div className="avatar-role">Fraud Analyst</div>
            </div>
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
                  />
                </div>
              </div>
              {error && <div className="error-message">{error}</div>}
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
          </div>
        </div>
      </div>

      {/* Signup Modal */}
      {showSignup && (
        <div className="modal-overlay open" onClick={() => setShowSignup(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-hdr">
              <h3>✨ Create Account</h3>
              <button className="modal-close" onClick={() => setShowSignup(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="signup-avatar">
                <div className="avatar-ring" onClick={() => document.getElementById('avatarUpload').click()}>
                  <img src={signupAvatar || '/Marvin.jpg'} alt="avatar" />
                </div>
                <input type="file" id="avatarUpload" accept="image/*" style={{display:'none'}} onChange={handleAvatarUpload} />
                <div className="hint">Click avatar to upload (optional)</div>
              </div>
              <div className="field">
                <label>Email Address</label>
                <div className="input-wrap">
                  <span className="input-icon">✉️</span>
                  <input type="email" value={signupEmail} onChange={(e) => setSignupEmail(e.target.value)} placeholder="you@example.com" />
                </div>
              </div>
              <div className="field">
                <label>Password</label>
                <div className="input-wrap">
                  <span className="input-icon">🔒</span>
                  <input type="password" value={signupPassword} onChange={(e) => setSignupPassword(e.target.value)} placeholder="Min 6 characters" />
                </div>
              </div>
              <div className="field">
                <label>Confirm Password</label>
                <div className="input-wrap">
                  <span className="input-icon">🔒</span>
                  <input type="password" value={signupConfirm} onChange={(e) => setSignupConfirm(e.target.value)} placeholder="Repeat password" />
                </div>
              </div>
              {signupError && <div className="error-message">{signupError}</div>}
              <div className="info-box">ℹ️ Your account will be active immediately. You can log in after registration.</div>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setShowSignup(false)}>Cancel</button>
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
