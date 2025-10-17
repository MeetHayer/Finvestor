import { Link } from 'react-router-dom';
import { useSafeQuery as useQuery } from '../lib/querySafe';
import { getJSON } from '../lib/http';

export default function WatchlistsPreview() {
  const { data, error, isLoading } = useQuery({
    queryKey: ['watchlists'],
    queryFn: () => getJSON('/watchlists'),
    staleTime: 60_000,
    enabled: true
  });

  return (
    <div className="rounded-2xl border bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Watchlists</h2>
        <Link to="/watchlist" className="text-blue-600 text-sm underline">Open</Link>
      </div>
      {isLoading && <div className="text-sm text-gray-500">Loading…</div>}
      {error && <div className="text-sm text-gray-500">(no watchlists created to display)</div>}
      {!isLoading && !error && (!data || data.length === 0) && (
        <div className="text-sm text-gray-500">(no watchlists created to display)</div>
      )}
      <ul className="space-y-2">
        {(data || []).slice(0,5).map(w => (
          <li key={w.id} className="flex items-center justify-between">
            <div className="font-medium">{w.name}</div>
            <span className="text-xs text-gray-400">#{w.id}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
