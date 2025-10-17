import { getJSON } from './http';

// Preload common tickers for instant loading
const COMMON_TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'SPY', 'QQQ', 'DIA'];

export function preloadCommonTickers() {
  // Preload in background without blocking UI
  COMMON_TICKERS.forEach(ticker => {
    setTimeout(() => {
      getJSON(`/data/${ticker}?range_days=365`).catch(() => {
        // Silently fail - this is just preloading
      });
    }, Math.random() * 2000); // Stagger requests
  });
}

// Preload on app start
export function initPreloading() {
  // Only preload if we're not in development
  if (import.meta.env.PROD) {
    preloadCommonTickers();
  }
}



