import api from './api';

export async function getJSON(url, config = {}) {
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort(), 8000); // 8s timeout - faster
  try {
    const { data } = await api.get(url, { 
      signal: ctrl.signal, 
      timeout: 6000, // 6s axios timeout
      ...config 
    });
    return data;
  } catch (e) {
    const msg = e?.response?.data?.detail || e.message || 'Request failed';
    throw new Error(msg);
  } finally {
    clearTimeout(id);
  }
}
