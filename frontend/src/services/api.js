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

// Response interceptor: handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('fg_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;