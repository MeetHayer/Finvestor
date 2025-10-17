/**
 * API service for Finvestor backend
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`🔵 API Request: ${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('🔴 API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for logging
api.interceptors.response.use(
  (response) => {
    console.log(`🟢 API Response: ${response.config.url}`, response.data);
    return response;
  },
  (error) => {
    console.error('🔴 API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Market Data
export const searchTickers = (query) => api.get(`/search?q=${encodeURIComponent(query)}`);
export const getMarketData = (symbol, rangeDays = 365) => api.get(`/data/${symbol}?range_days=${rangeDays}`);

// Watchlists
export const getWatchlists = () => api.get('/watchlists');
export const createWatchlist = (data) => api.post('/watchlists', data);
export const deleteWatchlist = (id) => api.delete(`/watchlists/${id}`);
export const getWatchlistTickers = (id) => api.get(`/watchlists/${id}/tickers`);
export const addToWatchlist = (id, symbol) => api.post(`/watchlists/${id}/tickers`, { symbol });
export const removeFromWatchlist = (id, symbol) => api.delete(`/watchlists/${id}/tickers/${symbol}`);

// Portfolios
export const getPortfolios = () => api.get('/portfolios');
export const createPortfolio = (data) => api.post('/portfolios', data);
export const deletePortfolio = (id) => api.delete(`/portfolios/${id}`);
export const getPortfolioHoldings = (id) => api.get(`/portfolios/${id}/holdings`);
export const addHolding = (id, data) => api.post(`/portfolios/${id}/holdings`, data);
export const removeHolding = (id, symbol) => api.delete(`/portfolios/${id}/holdings/${symbol}`);

export default api;