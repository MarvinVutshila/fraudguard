import axios from 'axios';

// Strict environment variable – must be set in your AWS environment
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

if (!API_BASE_URL) {
  throw new Error('VITE_API_BASE_URL environment variable is not set. Please set it in your AWS deployment environment.');
}

console.log('🔧 API_BASE_URL:', API_BASE_URL);

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
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
        
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        localStorage.removeItem('fg_token');
        localStorage.removeItem('fg_refresh_token');
        localStorage.removeItem('fg_role');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    localStorage.removeItem('fg_token');
    localStorage.removeItem('fg_refresh_token');
    localStorage.removeItem('fg_role');
    window.location.href = '/login';
    return Promise.reject(error);
  }
);

// ----- EXPORT ALL NECESSARY FUNCTIONS -----

// 1. Monitoring & Observability
export const getMonitoringStats = () => api.get('/monitoring/stats');
export const getApiLogs = (params) => api.get('/monitoring/request-logs', { params });
export const cleanupMonitoring = () => api.post('/monitoring/cleanup');

// 2. Transactions
export const getTransactions = (params) => api.get('/transactions', { params });
export const getTransaction = (id) => api.get(`/transactions/${id}`);
export const getOverrides = (limit = 100) => api.get(`/transactions/overrides?limit=${limit}`);
export const setOverride = (transactionId, newDecision, reason) => 
  api.post('/transactions/override', { transaction_id: transactionId, new_decision: newDecision, reason });

// 3. Predictions
export const predictTransaction = (data, explain = true) => 
  api.post(`/predict?explain=${explain}`, data);
export const predictBatch = (data) => api.post('/predict/batch', data);

// 4. Samples (for the Predict page quick-fill)
export const getSampleNormal = () => api.get('/samples/normal');
export const getSampleFraud = () => api.get('/samples/fraud');

// 5. Model Info
export const getModelInfo = () => api.get('/model/info');

// 6. Authentication
export const login = (credentials) => api.post('/auth/login', credentials);
export const register = (userData) => api.post('/auth/register', userData);
export const logout = (refreshToken) => api.post('/auth/logout', { refresh_token: refreshToken });
export const refreshToken = (token) => api.post('/auth/refresh', { refresh_token: token });
export const getCurrentUser = () => api.get('/auth/me');

// 7. Admin
// ✅ getPendingUsers – matches backend `/admin/users/pending`
export const getPendingUsers = () => api.get('/admin/users/pending');
// ✅ getUsers – fetch paginated user list
export const getUsers = (params) => api.get('/admin/users', { params });
// ✅ approveUser – sends `user_id` in body
export const approveUser = (userId, approve) => 
  api.post(`/admin/users/approve`, { user_id: userId, approve });
// Block, unblock, delete are correct
export const blockUser = (userId) => api.post(`/admin/users/${userId}/block`, {});
export const unblockUser = (userId) => api.post(`/admin/users/${userId}/unblock`);
export const deleteUser = (userId) => api.delete(`/admin/users/${userId}`);
// Stats and alerts
export const getUserStats = () => api.get('/admin/dashboard/summary');
export const getSecurityAlerts = () => api.get('/admin/alerts');
export const getLoginLogs = (params) => api.get('/admin/login-logs', { params });

// 8. 2FA
export const setup2FA = () => api.post('/2fa/setup');
export const verify2FASetup = (code) => api.post('/2fa/verify-setup', { code });
export const verify2FA = (username, code) => api.post('/2fa/verify', { username, code });
export const disable2FA = (code) => api.post('/2fa/disable', { code });

// 9. Avatar upload
export const uploadAvatar = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/users/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};

// 10. Health check
export const healthCheck = () => api.get('/health');

// === Export the base URL so other files can import it ===
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

// Default export of the configured api instance
export default api;