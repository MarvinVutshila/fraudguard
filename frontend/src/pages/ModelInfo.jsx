import { useState, useEffect } from 'react';
import api from '../services/api';

export default function ModelInfo() {
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [retrainStatus, setRetrainStatus] = useState(null);
  const [retraining, setRetraining] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

const fetchInfo = async () => {
  try {
    const res = await api.get('/model/info', {
      params: { _: Date.now() }   // <-- forces cache bust
    });
    console.log('📊 Model Info Response:', res.data);
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

  const pollRetrainStatus = async () => {
    try {
      const res = await api.get('/model/retrain/status');
      const status = res.data;
      setRetrainStatus(status);
      setStatusMsg(status.message || '');
      if (status.status === 'success' || status.status === 'failed' || status.status === 'cancelled') {
        setRetraining(false);
        if (status.status === 'success') fetchInfo();
      } else if (status.status === 'running') {
        setRetraining(true);
      }
    } catch (err) {
      console.error('Failed to fetch retrain status:', err);
    }
  };

  const startRetrain = async () => {
    setRetraining(true);
    setStatusMsg('Starting retraining...');
    try {
      // 🔥 NEW: use the fresh endpoint
      await api.post('/model/retrain-now');
      pollRetrainStatus();
      const interval = setInterval(pollRetrainStatus, 3000);
      window.retrainInterval = interval;
    } catch (err) {
      alert('Failed to start retraining: ' + (err.response?.data?.detail || err.message));
      setRetraining(false);
    }
  };

  const uploadDataset = async () => {
    if (!uploadFile) {
      alert('Please select a CSV file first.');
      return;
    }
    setUploading(true);
    const formData = new FormData();
    formData.append('file', uploadFile);
    try {
      await api.post('/model/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      alert('Dataset uploaded successfully! You can now retrain.');
      setUploadFile(null);
    } catch (err) {
      alert('Upload failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
    }
  };

  useEffect(() => {
    return () => {
      if (window.retrainInterval) clearInterval(window.retrainInterval);
    };
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
            <div style={{display:'flex', gap:'8px'}}>
              <button className="btn-secondary" onClick={fetchInfo}>↺ Refresh</button>
              <button 
                className="btn-primary" 
                onClick={startRetrain} 
                disabled={retraining}
                style={{background: retraining ? 'var(--text-muted)' : ''}}
              >
                {retraining ? '⏳ Retraining...' : '🔄 Retrain Model'}
              </button>
            </div>
          </div>
          <div>
            <div className="info-row"><span className="info-key">Model Type</span><span className="info-val">{info.model_type || 'XGBoost'}</span></div>
            <div className="info-row"><span className="info-key">Features</span><span className="info-val">{info.n_features || 30}</span></div>
            <div className="info-row"><span className="info-key">Optimal Threshold</span><span className="info-val">{info.optimal_threshold || '0.5'}</span></div>
            <div className="info-row"><span className="info-key">Max Allowed Amount</span><span className="info-val">${(info.max_allowed_amount || 25000).toFixed(2)}</span></div>
            <div className="info-row"><span className="info-key">Model Version</span><span className="info-val">{info.version || 'v3.0'}</span></div>
          </div>
        </div>

        {retrainStatus && (
          <div className="card" style={{borderColor: retrainStatus.status === 'failed' ? 'var(--danger)' : retrainStatus.status === 'success' ? 'var(--success)' : 'var(--border)'}}>
            <div className="card-header">
              <div className="card-title">📊 Retraining Status</div>
              <span className="status-badge" style={{background: retrainStatus.status === 'running' ? 'var(--warning)' : retrainStatus.status === 'success' ? 'var(--success)' : retrainStatus.status === 'failed' ? 'var(--danger)' : 'var(--text-muted)', color: '#fff'}}>
                {retrainStatus.status.toUpperCase()}
              </span>
            </div>
            <div className="info-row">
              <span className="info-key">Progress</span>
              <span className="info-val">{retrainStatus.progress}%</span>
            </div>
            <div className="mc-bar" style={{marginTop:'8px'}}>
              <div className="mc-fill" style={{width:`${retrainStatus.progress}%`, background: retrainStatus.status === 'failed' ? 'var(--danger)' : 'var(--accent)'}}></div>
            </div>
            <div className="info-row" style={{marginTop:'8px'}}>
              <span className="info-key">Message</span>
              <span className="info-val" style={{fontSize:'0.9rem', color: retrainStatus.status === 'failed' ? 'var(--danger)' : 'inherit'}}>
                {retrainStatus.message}
              </span>
            </div>
            {retrainStatus.status === 'running' && (
              <button className="btn-danger" style={{marginTop:'8px'}} onClick={async () => {
                await api.post('/model/retrain/cancel');
                alert('Cancellation requested.');
              }}>Cancel</button>
            )}
          </div>
        )}

        <div className="card">
          <div className="card-header">
            <div className="card-title">📁 Upload New Dataset</div>
          </div>
          <div style={{display:'flex', gap:'8px', alignItems:'center'}}>
            <input 
              type="file" 
              accept=".csv" 
              onChange={(e) => setUploadFile(e.target.files[0])}
              disabled={uploading}
            />
            <button className="btn-secondary" onClick={uploadDataset} disabled={uploading || !uploadFile}>
              {uploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
          <div className="card-sub" style={{marginTop:'4px'}}>
            Upload a CSV with columns: Time, V1..V28, Amount, Class
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