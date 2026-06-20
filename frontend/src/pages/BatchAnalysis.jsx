import { useState, useRef } from 'react';
import api from '../services/api';

export default function BatchAnalysis() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [progress, setProgress] = useState(0);
  const fileInput = useRef();

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (f) setFile(f);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  };

  const handleUpload = async () => {
    if (!file) return alert('Please select a CSV file.');
    setLoading(true);
    setProgress(10);
    try {
      const text = await file.text();
      const lines = text.split('\n').filter(l => l.trim());
      const headers = lines[0].split(',').map(h => h.trim());
      const transactions = [];
      for (let i = 1; i < lines.length; i++) {
        const vals = lines[i].split(',');
        const tx = { transaction_id: null, Amount: 0, Time: 0 };
        for (let j = 1; j <= 28; j++) tx['V'+j] = 0;
        headers.forEach((h, idx) => {
          const v = (vals[idx] || '').trim();
          if (h === 'transaction_id') tx.transaction_id = v;
          else if (h === 'Amount') tx.Amount = parseFloat(v) || 0;
          else if (h === 'Time') tx.Time = parseFloat(v) || 0;
          else if (/^V\d+$/i.test(h)) tx[h] = parseFloat(v) || 0;
        });
        transactions.push(tx);
        if (i % 50 === 0) setProgress(20 + Math.floor((i / lines.length) * 70));
      }
      setProgress(90);
      const res = await api.post('/predict/batch', { transactions });
      setResults(res.data.results || []);
      setProgress(100);
    } catch (err) {
      alert('Batch processing failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
      setTimeout(() => setProgress(0), 2000);
    }
  };

  const exportResults = () => {
    const rows = [['transaction_id','amount','probability','decision','risk_level']];
    results.forEach(r => rows.push([r.transaction_id || '', r.amount || 0, r.fraud_probability || 0, r.decision, r.risk_level || '']));
    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `batch_results_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="card-title">📁 Batch Transaction Analysis</div>
          <div className="card-sub">Upload a CSV and score all transactions at once</div>
        </div>
      </div>
      <div className="drop-zone" onDrop={handleDrop} onDragOver={e => e.preventDefault()}>
        <input type="file" ref={fileInput} accept=".csv" style={{display:'none'}} onChange={handleFileChange} />
        <div style={{fontSize:'2rem', marginBottom:'0.5rem'}}>📂</div>
        <div style={{fontWeight:'600'}}>{file ? file.name : 'Drop your CSV file here'}</div>
        <div style={{fontSize:'0.75rem', color:'var(--text-muted)'}}>or click to browse · Columns: transaction_id, Amount, Time, V1..V28</div>
        <button className="btn-primary" style={{marginTop:'1rem'}} onClick={() => fileInput.current.click()}>Choose File</button>
      </div>
      {file && (
        <div style={{marginTop:'1rem'}}>
          <button className="btn-primary" onClick={handleUpload} disabled={loading}>{loading ? 'Processing…' : 'Upload & Score'}</button>
          {loading && (
            <div style={{marginTop:'0.5rem'}}>
              <div style={{fontSize:'0.82rem', color:'var(--text-muted)'}}>Processing…</div>
              <div style={{height:'6px', background:'var(--surface3)', borderRadius:'99px'}}>
                <div style={{width:`${progress}%`, height:'100%', background:'linear-gradient(90deg, var(--accent), var(--cyan))', borderRadius:'99px'}}></div>
              </div>
            </div>
          )}
        </div>
      )}
      {results.length > 0 && (
        <div style={{marginTop:'1rem'}}>
          <div className="card-header">
            <div>
              <div className="card-title">Batch Results</div>
              <div className="card-sub">{results.length} transactions · {results.filter(r => r.decision === 'BLOCK').length} blocked · {results.filter(r => r.decision === 'REVIEW').length} for review</div>
            </div>
            <button className="btn-primary" onClick={exportResults}>⬇ Export CSV</button>
          </div>
          <div className="table-scroll">
            <table className="data-tbl">
              <thead><tr><th>ID</th><th>Amount</th><th>Probability</th><th>Decision</th><th>Risk Level</th></tr></thead>
              <tbody>
                {results.slice(0, 50).map((r, i) => (
                  <tr key={i}>
                    <td className="font-mono">{r.transaction_id || 'N/A'}</td>
                    <td>${(r.amount || 0).toFixed(2)}</td>
                    <td>{((r.fraud_probability || 0)*100).toFixed(1)}%</td>
                    <td><span className={`badge decision ${r.decision}`}>{r.decision}</span></td>
                    <td><span className={`badge risk ${(r.risk_level || '').toLowerCase()}`}>{r.risk_level || '—'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}