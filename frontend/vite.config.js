import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Auth endpoints (always proxy)
      '/auth': 'http://localhost:8000',

      // Transactions (GET) – this is API, not a page
      '/transactions': 'http://localhost:8000',

      // Predict – only proxy POST requests (API), not GET (page)
      '/predict': {
        target: 'http://localhost:8000',
        bypass: (req) => {
          if (req.method === 'POST') {
            return undefined; // proxy
          }
          return '/index.html';
        },
      },

      // Model info – only proxy /model/info (API), not /model (page)
      '/model': {
        target: 'http://localhost:8000',
        bypass: (req) => {
          if (req.url.startsWith('/model/info') || req.url.startsWith('/model/')) {
            return undefined; // proxy
          }
          return '/index.html';
        },
      },

      // Admin – proxy API calls, serve HTML for the page
      '/admin': {
        target: 'http://localhost:8000',
        bypass: (req) => {
          // API endpoints: /admin/users, /admin/login-logs, /admin/overrides, /admin/approve
          if (req.url.startsWith('/admin/users') ||
              req.url.startsWith('/admin/login-logs') ||
              req.url.startsWith('/admin/overrides') ||
              req.url.startsWith('/admin/approve')) {
            return undefined; // proxy to backend
          }
          // Plain /admin or /admin/ → serve React app
          return '/index.html';
        },
      },

      // Fallback for any other API-like endpoints
      '/users': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})