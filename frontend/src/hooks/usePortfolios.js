/**
 * Portfolio management hooks
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  getPortfolios,
  createPortfolio,
  deletePortfolio,
  addHolding,
  removeHolding
} from '../lib/api';

// Query: Get all portfolios
export const usePortfolios = () => {
  return useQuery({
    queryKey: ['portfolios'],
    queryFn: () => getPortfolios().then(r => r.data),
    staleTime: 2 * 60 * 1000,
  });
};

// Mutation: Create new portfolio
export const useCreatePortfolio = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data) => createPortfolio(data).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
    },
  });
};

// Mutation: Delete portfolio
export const useDeletePortfolio = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (portfolioId) => deletePortfolio(portfolioId).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
    },
  });
};

// Mutation: Add holding to portfolio
export const useAddHolding = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ portfolioId, data }) => addHolding(portfolioId, data).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
    },
  });
};

// Mutation: Remove holding from portfolio
export const useRemoveHolding = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ portfolioId, symbol }) => removeHolding(portfolioId, symbol).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
    },
  });
};

