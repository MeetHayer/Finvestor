import { useQuery, useInfiniteQuery, useQueries } from '@tanstack/react-query';

export const coerceEnabled = (v) => {
  if (typeof v === 'boolean' || typeof v === 'function') return v;
  if (v == null) return true;            // default to true when unspecified
  return !!v;                            // coerce anything else to boolean
};

export function useSafeQuery(opts) {
  const { enabled, queryFn, ...rest } = opts;
  const safe = { 
    ...rest, 
    enabled: coerceEnabled(enabled),
    staleTime: 30 * 60 * 1000, // 30 minutes - keep data fresh MUCH longer
    gcTime: 4 * 60 * 60 * 1000, // 4 hours - keep in cache MUCH longer
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
    retry: 1,
    retryDelay: 1000,
  };
  const safeFn = async () => {
    try { return await queryFn(); }
    catch (e) { console.error('Query error:', e); throw e; }
  };
  return useQuery({ ...safe, queryFn: safeFn });
}

export function useSafeInfiniteQuery(opts) {
  const { enabled, queryFn, ...rest } = opts;
  return useInfiniteQuery({ ...rest, enabled: coerceEnabled(enabled), queryFn });
}

export function useSafeQueries(options) {
  const mapped = options.queries.map(q => ({ ...q, enabled: coerceEnabled(q.enabled) }));
  return useQueries({ queries: mapped });
}
