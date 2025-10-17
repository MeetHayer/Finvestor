import { useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { Link } from 'react-router-dom';
import { useSafeQuery as useQuery } from '../lib/querySafe';
import { getJSON } from '../lib/http';
import IndexBenchmarks from '../sections/IndexBenchmarks';
import WatchlistsPreview from '../sections/WatchlistsPreview';
import TipsPanel from '../sections/TipsPanel';
import TickerSearch from '../components/TickerSearch';

export default function Home() {
  useEffect(() => { document.title = 'Finvestor — Home'; }, []);

  // A tiny ping so the page shows something if backend is up
  useQuery({
    queryKey: ['health'],
    queryFn: () => getJSON('/health'),    // backend exposes /api/health
    staleTime: 60_000,
    retry: 1,
    enabled: true
  });

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Home</h1>


      <IndexBenchmarks />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <WatchlistsPreview />
        </div>
        <div className="lg:col-span-1">
          <TipsPanel />
        </div>
      </div>

      <div className="text-sm text-gray-500">
        Need tickers? Try <Link to="/ticker/AAPL" className="text-blue-600 underline">AAPL</Link>,{' '}
        <Link to="/ticker/MSFT" className="text-blue-600 underline">MSFT</Link>,{' '}
        <Link to="/ticker/SPY" className="text-blue-600 underline">SPY</Link>.
      </div>
    </div>
  );
}