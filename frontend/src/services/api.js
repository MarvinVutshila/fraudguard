import axios from 'axios';

// You can set baseURL from environment, but for Vite proxy it's not needed
const api = axios.create({
  baseURL: '',  // empty means relative to the current origin
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: add token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('fg_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      console.warn('[api] No token found in localStorage');
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 and 403 (blocked)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail || '';

    // 401: Unauthorized → always redirect to login
    if (status === 401) {
      localStorage.removeItem('fg_token');
      window.location.href = '/login';
      return Promise.reject(error);
    }

    // 403: Forbidden – check if it's because the account is blocked/rejected/pending
    if (status === 403 && detail.includes('Account is')) {
      // e.g., "Account is blocked. Access denied."
      localStorage.removeItem('fg_token');
      window.location.href = '/login';
      return Promise.reject(error);
    }

    // For other 403 errors (e.g., "Admin access required"), just reject
    // so the component can show a user-friendly message.
    return Promise.reject(error);
  }
);

export default api;
