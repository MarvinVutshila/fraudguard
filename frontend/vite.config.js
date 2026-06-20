import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Auth endpoints (always proxy to backend)
      '/auth': 'http://localhost:8000',

      // Transactions API
      '/transactions': 'http://localhost:8000',

      // Predict – POST = API, GET = page
      '/predict': {
        target: 'http://localhost:8000',
        bypass: (req) => {
          if (req.method === 'POST') {
            return undefined; // proxy to backend
          }
          return '/index.html'; // serve React app for GET
        },
      },

      // Model – only /model/info is API, /model is page
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
          // API endpoints under /admin
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

      // ---- SPA ROUTES (add these!) ----
      '/history': {
        target: 'http://localhost:8000',
        bypass: () => '/index.html',
      },
      '/approval': {
        target: 'http://localhost:8000',
        bypass: () => '/index.html',
      },
      '/batch': {
        target: 'http://localhost:8000',
        bypass: () => '/index.html',
      },
      // If you have other routes like /monitoring, /model-info, etc., add them similarly.

      // Fallback API endpoints
      '/users': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
