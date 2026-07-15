import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000,
});

// Attach auth token from localStorage to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ps.token');
  if (token) {
    config.headers = { ...config.headers, Authorization: `Bearer ${token}` };
  }
  return config;
});

// Auto-logout on 401
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      const path = err?.config?.url || '';
      // Don't logout while on the login flow itself
      if (!path.includes('/auth/login')) {
        localStorage.removeItem('ps.token');
        localStorage.removeItem('ps.user');
        // Trigger a soft reload so AuthContext re-evaluates
        if (window.location.pathname !== '/') {
          window.location.href = '/';
        }
      }
    }
    return Promise.reject(err);
  }
);

export const screenshotUrl = (filename) => (filename ? `${API_BASE}/screenshots/${filename}` : null);

export const PortalsAPI = {
  list: () => api.get('/portals').then((r) => r.data),
};

export const DistributorsAPI = {
  list: () => api.get('/targets').then((r) => r.data),
  create: (payload) => api.post('/targets', payload).then((r) => r.data),
  update: (id, payload) => api.patch(`/targets/${id}`, payload).then((r) => r.data),
  remove: (id) => api.delete(`/targets/${id}`).then((r) => r.data),
  bulkSelect: (selected) => api.post('/targets/bulk-select', { selected }).then((r) => r.data),
  testLogin: (id) => api.post(`/targets/${id}/test-login`).then((r) => r.data),
};

export const HistoryAPI = {
  list: () => api.get('/history').then((r) => r.data),
  get: (id) => api.get(`/history/${id}`).then((r) => r.data),
  remove: (id) => api.delete(`/history/${id}`).then((r) => r.data),
};

export const ProductsAPI = {
  count: () => api.get('/products/count').then((r) => r.data),
  search: (q, limit = 20) => api.get('/products/search', { params: { q, limit } }).then((r) => r.data),
  clear: () => api.delete('/products/clear').then((r) => r.data),
  upload: (file) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/products/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    }).then((r) => r.data);
  },
};

export const ExtractAPI = {
  run: (product, quantity, targetIds) =>
    api.post('/extract', { product, quantity: quantity ? Number(quantity) : null, target_ids: targetIds }).then((r) => r.data),
  manualPick: (historyId, targetId, candidateName) =>
    api.post('/extract/manual-pick', { history_id: historyId, target_id: targetId, candidate_name: candidateName }).then((r) => r.data),
};

export const LiveconnectAPI = {
  status: () => api.get('/liveconnect/session').then((r) => r.data),
  begin: (mobile) => api.post('/liveconnect/session/begin', { mobile }).then((r) => r.data),
  verify: (pendingId, otp) => api.post('/liveconnect/session/verify', { pendingId, otp }).then((r) => r.data),
  clear: () => api.delete('/liveconnect/session').then((r) => r.data),
};

export const RetailioAPI = {
  status: () => api.get('/retailio/session').then((r) => r.data),
  begin: (mobile) => api.post('/retailio/session/begin', { mobile }).then((r) => r.data),
  verify: (pendingId, otp) => api.post('/retailio/session/verify', { pendingId, otp }).then((r) => r.data),
  clear: () => api.delete('/retailio/session').then((r) => r.data),
};

export default api;
