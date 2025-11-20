/**
 * Hook for fetching portfolio risk metrics
 */
import { useSafeQuery as useQuery } from '../lib/querySafe';
import { getJSON } from '../lib/http';

export const usePortfolioRisk = (portfolioId) => {
  return useQuery({
    queryKey: ['portfolioRisk', portfolioId],
    queryFn: () => getJSON(`/portfolios/${portfolioId}/risk`),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: Boolean(portfolioId),
  });
};

