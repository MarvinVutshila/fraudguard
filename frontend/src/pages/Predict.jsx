import { useState, useEffect } from 'react';
import api from '../services/api';

export default function Predict() {
  // --- Form state (initialized ONCE) ---
  const [form, setForm] = useState(() => {
    const initial = {
      transaction_id: '',
      Amount: 0,
      Time: 0,
    };
    for (let i = 1; i <= 28; i++) {
      initial[`V${i}`] = 0;
    }
    return initial;
  });

  // --- UI toggles ---
  const [showVFeatures, setShowVFeatures] = useState(false);
  const [showAllShap, setShowAllShap] = useState(false);
  const [explain, setExplain] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  // --- Clear result on mount (refresh) ---
  useEffect(() => {
    setResult(null);
  }, []);

  // --- Handle form changes ---
  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

  // --- Fetch a real sample from the backend ---
  const fillSample = async (type) => {
    setLoading(true);
    try {
      let endpoint = '';
      if (type === 'normal') endpoint = '/samples/normal';
      else if (type === 'suspicious' || type === 'fraud') endpoint = '/samples/fraud';
      else return;

      const res = await api.get(endpoint);
      const data = res.data;
      console.log('📥 Sample data from backend:', data); // <-- DEBUG

      // Build form with safe fallbacks for both uppercase/lowercase keys
      const newForm = {
        transaction_id: data.transaction_id || `SAMPLE-${Date.now()}`,
        Amount: Number(data.Amount ?? data.amount) || 0,
        Time: Number(data.Time ?? data.time) || 0,
      };
      for (let i = 1; i <= 28; i++) {
        const val = data[`V${i}`] ?? data[`v${i}`] ?? 0;
        newForm[`V${i}`] = Number(val);
      }
      setForm(newForm);
      setResult(null); // Clear previous prediction
    } catch (err) {
      alert('Failed to load sample: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // --- Clear form AND result ---
  const clearForm = () => {
    const empty = { transaction_id: '', Amount: 0, Time: 0 };
    for (let i = 1; i <= 28; i++) empty[`V${i}`] = 0;
    setForm(empty);
    setResult(null);
  };

  // --- Run prediction ---
  const handlePredict = async () => {
    setLoading(true);
    try {
      const payload = {
        transaction_id: form.transaction_id || `TXN-${Date.now()}`,
        Amount: Number(form.Amount) || 0,
        Time: Number(form.Time) || 0,
      };
      for (let i = 1; i <= 28; i++) {
        payload[`V${i}`] = Number(form[`V${i}`]) || 0;
      }
      const res = await api.post(`/predict?explain=${explain}`, payload);
      setResult(res.data);
    } catch (err) {
      alert('Prediction failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // --- Helper: get contribution safely ---
  const getContribution = (idx) => {
    if (!result || !result.explanation) return 0;
    const c = result.explanation.feature_contributions[idx];
    return c ? c.contribution : 0;
  };

  // --- Helper: top features ---
  const topFeatures = result?.explanation?.top_features || [];
  const featureContributions = result?.explanation?.feature_contributions || [];
  const maxAbs = featureContributions.length
    ? Math.max(...featureContributions.map(c => Math.abs(c.contribution || 0)), 0.001)
    : 1;

  return (
    <div className="predict-container">
      {/* Left: Form */}
      <div className="predict-form-card card">
        <div className="card-header">
          <div>
            <div className="card-title">🔍 Single Transaction Predict</div>
            <div className="card-sub">Enter features or use quick‑fill samples</div>
          </div>
        </div>

        <div className="predict-sample-buttons">
          <button className="btn-secondary" onClick={() => fillSample('normal')} disabled={loading}>
            Normal
          </button>
          <button className="btn-secondary" onClick={() => fillSample('suspicious')} disabled={loading}>
            Suspicious
          </button>
          <button className="btn-secondary" onClick={() => fillSample('fraud')} disabled={loading}>
            High-Risk
          </button>
          <button className="btn-secondary" onClick={clearForm} disabled={loading}>
            Clear
          </button>
        </div>

        {/* Main fields */}
        <div className="predict-main-fields">
          <div className="field-group">
            <label>Transaction ID</label>
            <input type="text" name="transaction_id" value={form.transaction_id} onChange={handleChange} disabled={loading} />
          </div>
          <div className="field-group">
            <label>Amount ($)</label>
            <input type="number" name="Amount" value={form.Amount} onChange={handleChange} step="0.01" disabled={loading} />
          </div>
          <div className="field-group">
            <label>Time (sec)</label>
            <input type="number" name="Time" value={form.Time} onChange={handleChange} step="1" disabled={loading} />
          </div>
        </div>

        {/* V-Features with toggle */}
        <div className="predict-v-section">
          <div className="v-section-header" onClick={() => setShowVFeatures(!showVFeatures)}>
            <span>V‑Features (V1–V28)</span>
            <span style={{ marginLeft: '0.5rem', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              {showVFeatures ? '▼' : '▶'} {showVFeatures ? 'hide' : 'show advanced'}
            </span>
          </div>
          {showVFeatures && (
            <div className="v-grid">
              {Array.from({ length: 28 }, (_, i) => i + 1).map(n => (
                <div key={n} className="v-field">
                  <label>V{n}</label>
                  <input
                    type="number"
                    name={`V${n}`}
                    value={form[`V${n}`]}
                    onChange={handleChange}
                    step="0.001"
                    disabled={loading}
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="predict-actions">
          <button className="btn-primary" onClick={handlePredict} disabled={loading}>
            {loading ? 'Predicting…' : 'Run Prediction →'}
          </button>
          <label className="explain-toggle">
            <input type="checkbox" checked={explain} onChange={e => setExplain(e.target.checked)} disabled={loading} />
            Include explanation
          </label>
          {result && (
            <button className="btn-secondary" onClick={clearForm} style={{ marginLeft: 'auto' }} disabled={loading}>
              Clear results
            </button>
          )}
        </div>
      </div>

      {/* Right: Results */}
      <div className="predict-results-card">
        {result ? (
          <div className="card result-card">
            {/* Probability circle + decision */}
            <div className="result-header">
              <div className="result-circle">
                <div className="result-percent">{((result.fraud_probability || 0) * 100).toFixed(1)}%</div>
                <div className="result-label">Fraud Prob.</div>
              </div>
              <div className="result-decision">
                <div>
                  <span className={`dec-badge ${result.decision}`}>{result.decision}</span>
                  <span className={`risk-badge ${(result.risk_level || '').toLowerCase()}`}>{result.risk_level}</span>
                </div>
                <div className="result-message">
                  {result.decision === 'APPROVE' ? '✅ Low risk. Transaction approved.' :
                   result.decision === 'REVIEW' ? '⚠️ Borderline. Sent to approval queue.' :
                   '🚫 High risk. Transaction blocked.'}
                </div>
                <div className="result-progress-bar">
                  <div style={{ width: `${(result.fraud_probability || 0) * 100}%` }}></div>
                </div>
              </div>
            </div>

            <div className="result-details">
              <div className="info-row">
                <span className="info-key">Transaction ID</span>
                <span className="font-mono">{result.transaction_id}</span>
              </div>
              <div className="info-row">
                <span className="info-key">Threshold</span>
                <span className="font-mono">{result.threshold || '—'}</span>
              </div>
            </div>

            {/* SHAP Explanation */}
            {explain && result.explanation && topFeatures.length > 0 && (
              <div className="result-shap">
                <div className="shap-header">
                  <span className="shap-title">🔬 SHAP Explanation</span>
                  <button
                    className="btn-secondary"
                    style={{ fontSize: '0.6rem', padding: '0.2rem 0.5rem' }}
                    onClick={() => setShowAllShap(!showAllShap)}
                    disabled={loading}
                  >
                    {showAllShap ? 'Show top 5' : 'Show all'}
                  </button>
                </div>
                <div className="shap-list">
                  {topFeatures.map((feature, idx) => {
                    const contribution = getContribution(idx);
                    const pct = Math.abs(contribution) / maxAbs * 100;
                    const isPositive = contribution > 0;
                    if (!showAllShap && idx >= 5) return null;
                    return (
                      <div key={feature} className="shap-row">
                        <span className="shap-feature" title={feature}>{feature}</span>
                        <div className="shap-bar-container">
                          <div className="shap-bar" style={{ width: `${pct}%`, background: isPositive ? 'var(--danger)' : 'var(--success)' }}></div>
                        </div>
                        <span className="shap-value">{isPositive ? '+' : ''}{contribution.toFixed(3)}</span>
                      </div>
                    );
                  })}
                </div>
                {topFeatures.length > 5 && !showAllShap && (
                  <div style={{ textAlign: 'center', marginTop: '0.4rem', fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                    + {topFeatures.length - 5} more features · click "Show all" to see full list
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="card placeholder-card">
            <div className="placeholder-icon">🔍</div>
            <div className="placeholder-text">Fill the form and run a prediction</div>
          </div>
        )}
      </div>
    </div>
  );
}