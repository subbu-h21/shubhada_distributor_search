import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000, // 2 min — real scraping can be slow
});

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
    return axios.post(`${API_BASE}/products/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000, // 5 min for large files
    }).then((r) => r.data);
  },
};

export const ExtractAPI = {
  run: (product, quantity, targetIds) =>
    api.post('/extract', { product, quantity: quantity ? Number(quantity) : null, target_ids: targetIds }).then((r) => r.data),
};

export default api;
