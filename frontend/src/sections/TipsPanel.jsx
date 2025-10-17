import { useState, useEffect } from 'react';

const tips = [
  '💡 Use range chips (1M/3M/6M/1Y) to zoom candlesticks for different timeframes.',
  '📊 Create a Portfolio with an inception date to track performance over time.',
  '⚡ Data calls retry once on failure and show friendly error messages.',
  '🔍 Search for any ticker symbol to view real-time charts and fundamentals.',
  '📈 Watchlists help you monitor multiple stocks in one place.',
  '💼 Portfolios track your actual holdings with entry dates and costs.',
  '📱 The app is fully responsive - works great on mobile devices.',
  '🔄 Charts update automatically with the latest market data.',
  '📋 Fundamentals show P/E ratio, market cap, beta, and 52-week highs/lows.',
  '🎯 Use the search bar on any ticker page to quickly switch between stocks.',
  '📊 Index benchmarks (SPY, QQQ, DIA) show overall market performance.',
  '⚙️ Data is cached for faster loading on repeat visits.',
  '🎨 Hover over chart elements for detailed price information.',
  '📈 Green candlesticks indicate price increases, red shows decreases.',
  '📊 Volume bars help identify trading activity and price confirmation.',
  '🔍 Type partial ticker symbols (e.g., "AAP") to see autocomplete suggestions.',
  '💡 Fundamentals data comes from multiple reliable sources (Finnhub, AlphaVantage).',
  '📱 Tap any ticker in search results to navigate to its detailed view.',
  '🎯 Use time range selectors to analyze short-term vs long-term trends.',
  '📊 Compare different stocks by navigating between ticker pages quickly.'
];

export default function TipsPanel() {
  const [currentTip, setCurrentTip] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTip((prev) => (prev + 1) % tips.length);
    }, 5000); // Rotate every 5 seconds

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="rounded-2xl border bg-white p-4 shadow-sm">
      <h2 className="text-lg font-semibold mb-3">Pro Tips</h2>
      <div className="relative h-20 overflow-hidden">
        <div 
          className="absolute inset-0 transition-transform duration-500 ease-in-out"
          style={{ transform: `translateY(-${currentTip * 100}%)` }}
        >
          {tips.map((tip, index) => (
            <div key={index} className="h-20 flex items-center text-sm text-gray-700">
              {tip}
            </div>
          ))}
        </div>
      </div>
      <div className="flex justify-center mt-2">
        <div className="flex gap-1">
          {tips.slice(0, Math.min(5, tips.length)).map((_, index) => (
            <div
              key={index}
              className={`w-2 h-2 rounded-full transition-colors ${
                index === currentTip % 5 ? 'bg-blue-600' : 'bg-gray-300'
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}