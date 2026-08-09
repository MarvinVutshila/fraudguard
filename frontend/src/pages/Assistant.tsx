import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import api from '../services/api';
import './Assistant.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const SUGGESTIONS = [
  'Summarize today\'s activity',
  'Explain this transaction',
  'Show blocked transactions',
  'Show recent overrides',
  'Explain model performance',
  'System health',
  'Failed login attempts',
  'Highest risk transactions',
  'API latency report',
  'Generate executive report',
];

type ResponseStyle = 'concise' | 'detailed' | 'table';

const Assistant: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [responseStyle, setResponseStyle] = useState<ResponseStyle>('concise');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim()) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Force token refresh
      await api.get('/auth/me');

      const token = localStorage.getItem('fg_token');
      const baseURL = api.defaults.baseURL;

      const response = await fetch(`${baseURL}/assistant/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: text,
          conversation_id: conversationId,
          style: responseStyle,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const json = line.slice(6);
            const payload = JSON.parse(json);
            if (payload.type === 'token') {
              assistantMessage.content += payload.content;
              setMessages(prev => {
                const updated = [...prev];
                const idx = updated.findIndex(m => m.id === assistantMessage.id);
                if (idx !== -1) {
                  updated[idx] = { ...assistantMessage };
                }
                return updated;
              });
            } else if (payload.type === 'done') {
              setIsLoading(false);
            }
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
      setIsLoading(false);

      if (error instanceof Error && error.message.includes('401')) {
        localStorage.removeItem('fg_token');
        localStorage.removeItem('fg_refresh_token');
        localStorage.removeItem('fg_role');
        window.location.href = '/login';
        return;
      }

      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `⚠️ Error: ${error instanceof Error ? error.message : 'Failed to fetch'}`,
          timestamp: new Date(),
        },
      ]);
    }
  };

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const clearChat = () => {
    setMessages([]);
    setConversationId(null);
  };

  const copyMessage = (content: string) => {
    navigator.clipboard.writeText(content);
  };

  return (
    <div className="assistant-container" style={{display:'flex', flexDirection:'column', height:'100vh', maxWidth:'1200px', margin:'0 auto', padding:'1rem'}}>
      {/* Header with style dropdown */}
      <div className="assistant-header" style={{display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', paddingBottom:'0.5rem', borderBottom:'1px solid var(--border)'}}>
        <div className="brand-area" style={{display:'flex', alignItems:'center', gap:'0.5rem'}}>
          <div className="avatar" style={{fontSize:'2rem'}}>🤖</div>
          <div>
            <h2 className="brand-title" style={{margin:0}}>FraudGuard AI</h2>
            <p className="brand-sub" style={{margin:0, fontSize:'0.8rem', opacity:0.7}}>Your intelligent fraud analyst assistant</p>
          </div>
        </div>
        <div className="header-controls" style={{display:'flex', gap:'0.5rem', alignItems:'center'}}>
          <select
            value={responseStyle}
            onChange={(e) => setResponseStyle(e.target.value as ResponseStyle)}
            className="style-select"
            style={{padding:'0.3rem 0.6rem', borderRadius:'4px', border:'1px solid var(--border)'}}
          >
            <option value="concise">Concise</option>
            <option value="detailed">Detailed</option>
            <option value="table">Table‑focused</option>
          </select>
          <button onClick={clearChat} className="btn-clear" style={{padding:'0.3rem 0.8rem', background:'transparent', border:'1px solid var(--border)', borderRadius:'4px'}}>
            Clear Chat
          </button>
        </div>
      </div>

      {/* Chat area */}
      <div className="chat-messages" style={{flex:1, overflowY:'auto', padding:'1rem 0'}}>
        {messages.length === 0 && (
          <div className="empty-state" style={{textAlign:'center', padding:'2rem'}}>
            <div className="empty-icon" style={{fontSize:'3rem'}}>💬</div>
            <p className="empty-greeting" style={{fontSize:'1.2rem'}}>Ask me anything about FraudGuard</p>
            <p className="empty-hint">Try one of these suggestions:</p>
            <div className="suggestions" style={{display:'flex', flexWrap:'wrap', gap:'0.5rem', justifyContent:'center'}}>
              {SUGGESTIONS.map(s => (
                <button key={s} onClick={() => sendMessage(s)} className="suggestion-btn" style={{padding:'0.4rem 0.8rem', background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:'20px', cursor:'pointer'}}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`message ${msg.role}`} style={{marginBottom:'1rem', display:'flex', flexDirection:'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start'}}>
            <div className="message-header" style={{display:'flex', justifyContent:'space-between', width:'100%', padding:'0 0.2rem'}}>
              <span className="role-label" style={{fontWeight:'bold'}}>
                {msg.role === 'user' ? '👤 You' : '🤖 FraudGuard AI'}
              </span>
              <div className="message-actions">
                <span className="timestamp" style={{fontSize:'0.7rem', opacity:0.6}}>{msg.timestamp.toLocaleTimeString()}</span>
                {msg.role === 'assistant' && (
                  <button onClick={() => copyMessage(msg.content)} className="copy-btn" style={{marginLeft:'0.5rem', background:'none', border:'none', cursor:'pointer'}} title="Copy response">
                    📋
                  </button>
                )}
              </div>
            </div>
            <div className="message-content" style={{maxWidth:'85%', padding:'0.8rem', background: msg.role === 'user' ? 'var(--accent)' : 'var(--surface2)', borderRadius:'8px', wordBreak:'break-word'}}>
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="typing-indicator" style={{display:'flex', gap:'0.3rem', padding:'0.5rem'}}>
            <span>●</span><span>●</span><span>●</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <form className="input-area" onSubmit={handleSend} style={{display:'flex', gap:'0.5rem', paddingTop:'0.5rem', borderTop:'1px solid var(--border)'}}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything about your fraud data..."
          disabled={isLoading}
          style={{flex:1, padding:'0.6rem', borderRadius:'4px', border:'1px solid var(--border)'}}
        />
        <button type="submit" disabled={isLoading || !input.trim()} style={{padding:'0.6rem 1.2rem', background:'var(--accent)', color:'#fff', border:'none', borderRadius:'4px', cursor:'pointer'}}>
          Send
        </button>
      </form>
    </div>
  );
};

export default Assistant;