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

// New option for response style
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
          style: responseStyle,   // <-- pass the selected style
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
    <div className="assistant-container">
      {/* Header with style dropdown */}
      <div className="assistant-header">
        <div className="brand-area">
          <div className="avatar">🤖</div>
          <div>
            <h2 className="brand-title">FraudGuard AI</h2>
            <p className="brand-sub">Your intelligent fraud analyst assistant</p>
          </div>
        </div>
        <div className="header-controls">
          <select
            value={responseStyle}
            onChange={(e) => setResponseStyle(e.target.value as ResponseStyle)}
            className="style-select"
          >
            <option value="concise">Concise</option>
            <option value="detailed">Detailed</option>
            <option value="table">Table‑focused</option>
          </select>
          <button onClick={clearChat} className="btn-clear">
            Clear Chat
          </button>
        </div>
      </div>

      {/* Chat area – unchanged */}
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">💬</div>
            <p className="empty-greeting">Ask me anything about FraudGuard</p>
            <p className="empty-hint">Try one of these suggestions:</p>
            <div className="suggestions">
              {SUGGESTIONS.map(s => (
                <button key={s} onClick={() => sendMessage(s)} className="suggestion-btn">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`message ${msg.role}`}>
            <div className="message-header">
              <span className="role-label">
                {msg.role === 'user' ? (
                  <span className="user-icon">👤</span>
                ) : (
                  <span className="assistant-icon">🤖</span>
                )}
                {msg.role === 'user' ? 'You' : 'FraudGuard AI'}
              </span>
              <div className="message-actions">
                <span className="timestamp">{msg.timestamp.toLocaleTimeString()}</span>
                {msg.role === 'assistant' && (
                  <button onClick={() => copyMessage(msg.content)} className="copy-btn" title="Copy response">
                    📋
                  </button>
                )}
              </div>
            </div>
            <div className="message-content">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="typing-indicator">
            <span>●</span><span>●</span><span>●</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area – unchanged */}
      <form className="input-area" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything about your fraud data..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
};

export default Assistant;