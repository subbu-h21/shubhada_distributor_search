import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

export const PortalsAPI = {
  list: () => api.get('/portals').then((r) => r.data),
};

export const TargetsAPI = {
  list: () => api.get('/targets').then((r) => r.data),
  create: (payload) => api.post('/targets', payload).then((r) => r.data),
  update: (id, payload) => api.patch(`/targets/${id}`, payload).then((r) => r.data),
  remove: (id) => api.delete(`/targets/${id}`).then((r) => r.data),
  bulkSelect: (selected) => api.post('/targets/bulk-select', { selected }).then((r) => r.data),
};

export const HistoryAPI = {
  list: () => api.get('/history').then((r) => r.data),
  get: (id) => api.get(`/history/${id}`).then((r) => r.data),
  remove: (id) => api.delete(`/history/${id}`).then((r) => r.data),
};

export const ExtractAPI = {
  run: (product, targetIds) =>
    api.post('/extract', { product, target_ids: targetIds }).then((r) => r.data),
};

export default api;
