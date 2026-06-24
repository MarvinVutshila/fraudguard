import axios from 'axios';

// Use environment variable with fallback for development
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
                     (import.meta.env.DEV ? 'http://localhost:8000' : 'https://fraudguard-434w.onrender.com');

console.log('🔧 API_BASE_URL:', API_BASE_URL); // This will show which URL is being used

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// Request interceptor to add token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('fg_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Don't retry if already retrying or if not a 401
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }
    
    originalRequest._retry = true;
    
    const refreshToken = localStorage.getItem('fg_refresh_token');
    if (refreshToken) {
      try {
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken
        });
        
        const { access_token } = response.data;
        localStorage.setItem('fg_token', access_token);
        
        // Update the original request with new token
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed - logout user
        localStorage.removeItem('fg_token');
        localStorage.removeItem('fg_refresh_token');
        localStorage.removeItem('fg_role');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    // No refresh token - redirect to login
    localStorage.removeItem('fg_token');
    localStorage.removeItem('fg_refresh_token');
    localStorage.removeItem('fg_role');
    window.location.href = '/login';
    return Promise.reject(error);
  }
);

export default api;
