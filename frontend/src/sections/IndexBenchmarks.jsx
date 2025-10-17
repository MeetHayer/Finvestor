import { useSafeQuery as useQuery } from '../lib/querySafe';
import { getJSON } from '../lib/http';

const symbols = ['SPY','QQQ','DIA']; // simple ETF proxies

function Card({ title, value, changeDollar, changePct, week52High, week52Low, etfInfo, description }) {
  const isPositive = changeDollar >= 0;
  return (
    <div className="rounded-2xl border bg-white p-4 shadow-sm">
      <div className="text-sm text-gray-500">{title}</div>
      <div className="text-xs text-blue-600 font-medium mb-1">{etfInfo}</div>
      <div className="text-2xl font-semibold">${value}</div>
      <div className="text-xs text-gray-500 mb-1">Today's Change</div>
      <div className={`text-sm ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
        {isPositive ? '+' : ''}${changeDollar?.toFixed(2)} ({isPositive ? '+' : ''}{changePct}%)
      </div>
      <div className="text-xs text-gray-400 mt-1">
        52W: ${week52High?.toFixed(2)} / ${week52Low?.toFixed(2)}
      </div>
      <div className="text-xs text-gray-500 mt-3 leading-relaxed">
        {description}
      </div>
    </div>
  );
}

export default function IndexBenchmarks() {
  const query = useQuery({
    queryKey: ['benchmarks'],
    queryFn: async () => {
      try {
        // Use the new dedicated benchmarks endpoint
        const data = await getJSON('/benchmarks');
        
        const out = {};
        for (const symbol of symbols) {
          const benchmarkData = data[symbol];
          if (benchmarkData) {
            const latest = benchmarkData.latest || {};
            const close = latest.close || 0;
            const prevClose = latest.prevClose || close;
            const chg = close - prevClose;
            const pct = prevClose ? (chg / prevClose) * 100 : 0;
            
            // Get 52-week high/low from fundamentals
            const week52High = benchmarkData.fundamentals?.fiftyTwoWeekHigh || 0;
            const week52Low = benchmarkData.fundamentals?.fiftyTwoWeekLow || 0;
            
            out[symbol] = { 
              close, 
              changeDollar: chg,
              changePct: +pct.toFixed(2),
              week52High,
              week52Low
            };
          } else {
            // Fallback if symbol not found
            out[symbol] = { close: 0, changeDollar: 0, changePct: 0, week52High: 0, week52Low: 0 };
          }
        }
        return out;
      } catch (e) {
        // Fallback to individual API calls if benchmarks endpoint fails
        console.warn('Benchmarks endpoint failed, falling back to individual calls:', e);
        
        const out = {};
        for (const s of symbols) {
          try {
            const data = await getJSON(`/data/${s}?range_days=5`);
            const latest = data?.latest || {};
            const close = latest.close || 0;
            const prevClose = latest.prevClose || close;
            const chg = close - prevClose;
            const pct = prevClose ? (chg / prevClose) * 100 : 0;
            
            const week52High = data?.fundamentals?.fiftyTwoWeekHigh || data?.fundamentals?.week_52_high || 0;
            const week52Low = data?.fundamentals?.fiftyTwoWeekLow || data?.fundamentals?.week_52_low || 0;
            
            out[s] = { 
              close, 
              changeDollar: chg,
              changePct: +pct.toFixed(2),
              week52High,
              week52Low
            };
          } catch (e) {
            out[s] = { close: 0, changeDollar: 0, changePct: 0, week52High: 0, week52Low: 0 };
          }
        }
        return out;
      }
    },
    staleTime: 60_000,
    enabled: true
  });

  const d = query.data || {};
  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Index Benchmarks</h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card 
          title="S&P 500 (SPY)" 
          etfInfo="SPDR S&P 500 ETF Trust • $500B AUM • 0.09% expense ratio"
          value={d.SPY ? d.SPY.close.toFixed(2) : '—'}
          changeDollar={d.SPY?.changeDollar}
          changePct={d.SPY?.changePct}
          week52High={d.SPY?.week52High}
          week52Low={d.SPY?.week52Low}
          description="Tracks 500 largest US companies. Includes Apple, Microsoft, Amazon, Tesla. Historical avg: 10% annual return. Most diversified US market exposure."
        />
        <Card 
          title="Nasdaq 100 (QQQ)" 
          etfInfo="Invesco QQQ Trust • $250B AUM • 0.20% expense ratio"
          value={d.QQQ ? d.QQQ.close.toFixed(2) : '—'}
          changeDollar={d.QQQ?.changeDollar}
          changePct={d.QQQ?.changePct}
          week52High={d.QQQ?.week52High}
          week52Low={d.QQQ?.week52Low}
          description="100 largest non-financial Nasdaq stocks. Heavy tech focus: Apple, Microsoft, Google, Amazon. Higher volatility, growth-oriented. Avg: 12% annual return."
        />
        <Card 
          title="Dow Jones (DIA)" 
          etfInfo="SPDR Dow Jones Industrial Average ETF • $35B AUM • 0.16% expense ratio"
          value={d.DIA ? d.DIA.close.toFixed(2) : '—'}
          changeDollar={d.DIA?.changeDollar}
          changePct={d.DIA?.changePct}
          week52High={d.DIA?.week52High}
          week52Low={d.DIA?.week52Low}
          description="30 large-cap US companies. Price-weighted index. Includes Coca-Cola, McDonald's, Boeing, Disney. Conservative, dividend-focused. Avg: 7% annual return."
        />
      </div>
      {query.error && <div className="text-sm text-red-600 mt-2">Benchmarks fallback: {String(query.error.message || query.error)}</div>}
    </div>
  );
}
