import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, TrendingUp } from 'lucide-react';
import { useSafeQuery as useQuery } from '../lib/querySafe';
import { getJSON } from '../lib/http';

export default function TickerSearch({ placeholder = "Search tickers...", className = "", onSelect }) {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [showResults, setShowResults] = useState(false);
  const navigate = useNavigate();
  const searchRef = useRef(null);

  // Debounce search query (300ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  // Fetch results
  const { data: results = [], isLoading } = useQuery({
    queryKey: ['tickerSearch', debouncedQuery],
    queryFn: () => getJSON(`/search?q=${debouncedQuery}`),
    staleTime: 10 * 60 * 1000, // 10 minutes
    enabled: Boolean(debouncedQuery && debouncedQuery.trim().length > 0),
  });

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowResults(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (symbol) => {
    if (onSelect) {
      onSelect(symbol);
    } else {
      navigate(`/ticker/${symbol}`);
    }
    setQuery('');
    setShowResults(false);
  };

  return (
    <div ref={searchRef} className={`relative ${className}`}>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setShowResults(true);
          }}
          onFocus={() => setShowResults(true)}
          placeholder={placeholder}
          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all"
        />
      </div>

      {/* Results Dropdown */}
      {showResults && query && (
        <div className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-96 overflow-y-auto">
          {isLoading ? (
            <div className="p-4 text-center text-gray-500">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600 mx-auto"></div>
            </div>
          ) : results.length > 0 ? (
            <div className="py-2">
              {results.map((ticker) => (
                <button
                  key={ticker.symbol}
                  onClick={() => handleSelect(ticker.symbol)}
                  className="w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors flex items-center justify-between group"
                >
                  <div>
                    <div className="font-semibold text-gray-900">{ticker.symbol}</div>
                    <div className="text-sm text-gray-500 truncate">{ticker.name}</div>
                  </div>
                  <TrendingUp className="w-4 h-4 text-gray-400 group-hover:text-primary-600 transition-colors" />
                </button>
              ))}
            </div>
          ) : (
            <div className="p-4 text-center text-gray-500">
              No results found for "{query}"
            </div>
          )}
        </div>
      )}
    </div>
  );
}

