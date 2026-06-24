import React from 'react';
import { useTheme } from '../context/ThemeContext';

const ThemeToggle = () => {
  const { isDarkMode, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="theme-toggle"
      aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
      style={{
        background: 'var(--surface2)',
        border: '1px solid var(--border)',
        borderRadius: '8px',
        padding: '6px 10px',
        cursor: 'pointer',
        color: 'var(--text)',
        fontSize: '1.1rem',
        transition: 'all 0.2s ease',
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
      }}
    >
      {isDarkMode ? '☀️' : '🌙'}
      <span style={{ fontSize: '0.7rem', fontWeight: 500 }}>
        {isDarkMode ? 'Light' : 'Dark'}
      </span>
    </button>
  );
};

export default ThemeToggle;
