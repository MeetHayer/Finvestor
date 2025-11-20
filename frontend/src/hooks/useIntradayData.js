/**
 * Hook for fetching 1-minute intraday data
 */
import { useSafeQuery as useQuery } from '../lib/querySafe';
import { getJSON } from '../lib/http';

export const useIntradayData = (symbol, periodDays = 7) => {
  return useQuery({
    queryKey: ['intradayData', symbol, periodDays],
    queryFn: () => getJSON(`/tickers/${symbol}/intraday?period_days=${periodDays}&interval=1m`),
    staleTime: 60 * 1000, // 1 minute - intraday data changes frequently
    enabled: Boolean(symbol),
    retry: 1, // Intraday data may fail more often
  });
};

