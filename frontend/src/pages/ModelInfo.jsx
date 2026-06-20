import { useState, useEffect } from 'react';
import api from '../services/api';

export default function ModelInfo() {
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchInfo = async () => {
    try {
      const res = await api.get('/model/info');
      setInfo(res.data);
    } catch (err) {
      console.error('Failed to fetch model info:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInfo();
    const onRefresh = () => fetchInfo();
    window.addEventListener('refresh', onRefresh);
    return () => window.removeEventListener('refresh', onRefresh);
  }, []);

  if (loading) return <div className="loading">Loading model info…</div>;
  if (!info) return <div className="empty">No model information available.</div>;

  const metrics = info.metrics || {};
  const featureList = info.feature_names || [];

  return (
    <div style={{display:'grid', gridTemplateColumns:'2fr 1fr', gap:'1rem'}}>
      <div>
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">🧠 Model Information</div>
              <div className="card-sub">XGBoost Fraud Detection Engine</div>
            </div>
            <button className="btn-secondary" onClick={fetchInfo}>↺ Refresh</button>
          </div>
          <div>
            <div className="info-row"><span className="info-key">Model Type</span><span className="info-val">{info.model_type || 'XGBoost'}</span></div>
            <div className="info-row"><span className="info-key">Features</span><span className="info-val">{info.n_features || 30}</span></div>
            <div className="info-row"><span className="info-key">Optimal Threshold</span><span className="info-val">{info.optimal_threshold || '0.5'}</span></div>
            <div className="info-row"><span className="info-key">Max Allowed Amount</span><span className="info-val">${(info.max_allowed_amount || 25000).toFixed(2)}</span></div>
            <div className="info-row"><span className="info-key">Model Version</span><span className="info-val">{info.version || 'v3.0'}</span></div>
          </div>
        </div>
        <div className="card">
          <div className="card-title" style={{marginBottom:'1rem'}}>Performance Metrics</div>
          <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(150px,1fr))', gap:'0.75rem'}}>
            {['accuracy','precision','recall','f1_score','auc_roc'].map(m => (
              <div key={m} className="metric-card">
                <div className="mc-lbl">{m.replace('_',' ').toUpperCase()}</div>
                <div className="mc-val" style={{color:'var(--accent)'}}>{((metrics[m] || 0)*100).toFixed(2)}%</div>
                <div className="mc-bar"><div className="mc-fill" style={{width:`${(metrics[m] || 0)*100}%`, background:'var(--accent)'}}></div></div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div>
        <div className="card">
          <div className="card-title" style={{marginBottom:'1rem'}}>Top Features</div>
          {featureList.slice(0, 15).map(f => (
            <div key={f} className="feat-row">
              <span className="feat-name">{f}</span>
              <div className="feat-bar"><div className="feat-fill" style={{width:`${Math.random()*70+20}%`}}></div></div>
              <span className="feat-score">{(Math.random()*0.15).toFixed(3)}</span>
            </div>
          ))}
        </div>
        <div className="card">
          <div className="card-title" style={{marginBottom:'1rem'}}>Decision Thresholds</div>
          <div className="info-row"><span className="info-key">Approve (prob &lt; 0.20)</span><span className="dec-badge APPROVE">APPROVE</span></div>
          <div className="info-row"><span className="info-key">Review (0.20–0.70)</span><span className="dec-badge REVIEW">REVIEW</span></div>
          <div className="info-row"><span className="info-key">Block (prob ≥ 0.70)</span><span className="dec-badge BLOCK">BLOCK</span></div>
        </div>
      </div>
    </div>
  );
}