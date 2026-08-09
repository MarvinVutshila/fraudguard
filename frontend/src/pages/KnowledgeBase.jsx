import { useState, useEffect } from 'react';
import api from '../services/api';
import './KnowledgeBase.css';

export default function KnowledgeBase() {
  const [entries, setEntries] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState(null);
  const [form, setForm] = useState({ question: '', answer: '', category: 'General', keywords: '' });

  const fetchEntries = async (page = 1) => {
    setLoading(true);
    try {
      const limit = 20;
      const offset = (page - 1) * limit;
      const res = await api.get('/knowledge_base/', { params: { search, limit, offset } });
      setEntries(res.data.entries);
      setTotal(res.data.total);
    } catch (err) {
      console.error('Failed to fetch KB entries:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntries(1);
  }, [search]);

  const handleDelete = async (id) => {
    if (!confirm('Delete this entry?')) return;
    try {
      await api.delete(`/knowledge_base/${id}`);
      fetchEntries();
    } catch (err) {
      alert('Failed to delete');
    }
  };

  const openCreate = () => {
    setEditingEntry(null);
    setForm({ question: '', answer: '', category: 'General', keywords: '' });
    setModalOpen(true);
  };

  const openEdit = (entry) => {
    setEditingEntry(entry);
    setForm({
      question: entry.question,
      answer: entry.answer,
      category: entry.category,
      keywords: entry.keywords || '',
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    if (!form.question.trim() || !form.answer.trim()) {
      alert('Question and Answer are required.');
      return;
    }
    try {
      if (editingEntry) {
        await api.put(`/knowledge_base/${editingEntry.id}`, form);
      } else {
        await api.post('/knowledge_base', form);
      }
      setModalOpen(false);
      fetchEntries();
    } catch (err) {
      alert('Failed to save entry');
    }
  };

  const truncate = (text, max = 100) => {
    if (!text) return '';
    return text.length > max ? text.slice(0, max) + '…' : text;
  };

  return (
    <div className="kb-container">
      <div className="kb-header">
        <h2>📚 Knowledge Base</h2>
        <div className="kb-actions">
          <input
            type="text"
            placeholder="Search questions or answers..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="kb-search"
          />
          <button className="btn-primary" onClick={openCreate}>+ Add Entry</button>
        </div>
      </div>

      <div className="kb-table-wrap">
        <table className="kb-table">
          <thead>
            <tr>
              <th>Question</th>
              <th>Answer</th>
              <th className="hide-on-mobile">Category</th>
              <th className="hide-on-mobile">Usage</th>
              <th className="hide-on-mobile">Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan="6" className="loading-cell">Loading...</td></tr>
            ) : entries.length === 0 ? (
              <tr><td colSpan="6" className="empty-cell">No entries found</td></tr>
            ) : (
              entries.map((entry) => (
                <tr key={entry.id}>
                  <td className="kb-question">{entry.question}</td>
                  <td className="kb-answer">{truncate(entry.answer)}</td>
                  <td className="hide-on-mobile"><span className="kb-category">{entry.category}</span></td>
                  <td className="hide-on-mobile">{entry.usage_count || 0}</td>
                  <td className="hide-on-mobile">{new Date(entry.created_at).toLocaleDateString()}</td>
                  <td>
                    <button className="btn-secondary" onClick={() => openEdit(entry)}>✎</button>
                    <button className="btn-danger-soft" onClick={() => handleDelete(entry.id)}>🗑</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        <div className="kb-footer">
          <span>Total: {total} entries</span>
        </div>
      </div>

      {modalOpen && (
        <div className="modal-overlay open" onClick={() => setModalOpen(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-hdr">
              <h3>{editingEntry ? 'Edit Entry' : 'Add Entry'}</h3>
              <button className="modal-close" onClick={() => setModalOpen(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="field">
                <label>Question *</label>
                <input value={form.question} onChange={(e) => setForm({...form, question: e.target.value})} />
              </div>
              <div className="field">
                <label>Answer *</label>
                <textarea
                  rows={4}
                  value={form.answer}
                  onChange={(e) => setForm({...form, answer: e.target.value})}
                />
              </div>
              <div className="field">
                <label>Category</label>
                <select value={form.category} onChange={(e) => setForm({...form, category: e.target.value})}>
                  <option value="General">General</option>
                  <option value="Model">Model</option>
                  <option value="System">System</option>
                  <option value="Security">Security</option>
                  <option value="Compliance">Compliance</option>
                </select>
              </div>
              <div className="field">
                <label>Keywords (comma‑separated, for better matching)</label>
                <input value={form.keywords} onChange={(e) => setForm({...form, keywords: e.target.value})} />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setModalOpen(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleSave}>Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}