/**
 * Individual portfolio detail hook
 */
import { useQuery } from '@tanstack/react-query';
import { getPortfolios } from '../lib/api';

// Query: Get single portfolio by ID
// Since we don't have a dedicated /portfolios/{id} endpoint yet,
// we fetch all portfolios and filter client-side
export const usePortfolioById = (portfolioId) => {
  return useQuery({
    queryKey: ['portfolio', portfolioId],
    queryFn: async () => {
      const response = await getPortfolios();
      const portfolios = response.data;
      const portfolio = portfolios.find(p => p.id === portfolioId);
      
      if (!portfolio) {
        throw new Error(`Portfolio ${portfolioId} not found`);
      }
      
      return portfolio;
    },
    enabled: Boolean(portfolioId),
    staleTime: 2 * 60 * 1000,
  });
};

