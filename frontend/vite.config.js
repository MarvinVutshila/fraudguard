import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  // Load environment variables from .env files
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.VITE_API_BASE_URL || 'http://localhost:8000';

  return {
    plugins: [react()],
    server: {
      proxy: {
        // Auth endpoints
        '/auth': apiTarget,

        // Transactions API
        '/transactions': apiTarget,

        // Predict – POST = API, GET = page
        '/predict': {
          target: apiTarget,
          bypass: (req) => {
            if (req.method === 'POST') {
              return undefined; // proxy to backend
            }
            return '/index.html'; // serve React app for GET
          },
        },

        // Model – only /model/info is API, /model is page
        '/model': {
          target: apiTarget,
          bypass: (req) => {
            if (req.url.startsWith('/model/info') || req.url.startsWith('/model/')) {
              return undefined; // proxy
            }
            return '/index.html';
          },
        },

        // Admin – proxy API calls, serve HTML for the page
        '/admin': {
          target: apiTarget,
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

        // SPA routes – always serve index.html
        '/history': {
          target: apiTarget,
          bypass: () => '/index.html',
        },
        '/approval': {
          target: apiTarget,
          bypass: () => '/index.html',
        },
        '/batch': {
          target: apiTarget,
          bypass: () => '/index.html',
        },
        // Add other SPA routes as needed...

        // Fallback API endpoints
        '/users': apiTarget,
        '/health': apiTarget,
      },
    },
  };
});