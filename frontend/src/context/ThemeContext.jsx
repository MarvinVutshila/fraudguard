import React, { createContext, useState, useContext, useEffect } from 'react';

const ThemeContext = createContext();

export const ThemeProvider = ({ children }) => {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    // Check localStorage first
    const savedTheme = localStorage.getItem('theme');
    console.log('Saved theme from localStorage:', savedTheme);
    
    if (savedTheme) {
      return savedTheme === 'dark';
    }
    // Fall back to system preference
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    console.log('System prefers dark:', systemPrefersDark);
    return systemPrefersDark;
  });

  useEffect(() => {
    console.log('Theme changed to:', isDarkMode ? 'dark' : 'light');
    
    // Apply theme to document using ONLY data-theme attribute
    if (isDarkMode) {
      document.documentElement.setAttribute('data-theme', 'dark');
      // REMOVED: document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
      // REMOVED: document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
    
    // Log what's applied
    console.log('data-theme attribute:', document.documentElement.getAttribute('data-theme'));
    console.log('classList:', document.documentElement.classList);
  }, [isDarkMode]);

  const toggleTheme = () => {
    console.log('Toggle clicked, current:', isDarkMode ? 'dark' : 'light');
    setIsDarkMode(!isDarkMode);
  };

  return (
    <ThemeContext.Provider value={{ isDarkMode, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
