/**
 * React Query hooks for data fetching and caching
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  searchTickers, 
  getMarketData, 
  getWatchlists, 
  createWatchlist, 
  deleteWatchlist,
  addToWatchlist,
  removeFromWatchlist,
  getPortfolios,
  createPortfolio,
  deletePortfolio,
  addHolding,
  removeHolding
} from './api';

// Market Data Queries
export const useMarketData = (symbol, rangeDays = 365) => {
  return useQuery({
    queryKey: ['marketData', symbol, rangeDays],
    queryFn: () => getMarketData(symbol, rangeDays).then(r => r.data),
    enabled: Boolean(symbol && symbol.trim().length > 0),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });
};

export const useTickerSearch = (query) => {
  return useQuery({
    queryKey: ['tickerSearch', query],
    queryFn: () => searchTickers(query).then(r => r.data),
    enabled: Boolean(query && query.trim().length > 0),
    staleTime: 5 * 60 * 1000,
  });
};

// Watchlist Queries
export const useWatchlists = () => {
  return useQuery({
    queryKey: ['watchlists'],
    queryFn: () => getWatchlists().then(r => r.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateWatchlist = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data) => createWatchlist(data).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] });
    },
  });
};

export const useDeleteWatchlist = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (watchlistId) => deleteWatchlist(watchlistId).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] });
    },
  });
};

export const useAddToWatchlist = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ watchlistId, symbol }) => addToWatchlist(watchlistId, symbol).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] });
    },
  });
};

export const useRemoveFromWatchlist = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ watchlistId, symbol }) => removeFromWatchlist(watchlistId, symbol).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] });
    },
  });
};

// Portfolio Queries
export const usePortfolios = () => {
  return useQuery({
    queryKey: ['portfolios'],
    queryFn: () => getPortfolios().then(r => r.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreatePortfolio = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data) => createPortfolio(data).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
    },
  });
};

export const useDeletePortfolio = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (portfolioId) => deletePortfolio(portfolioId).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
    },
  });
};

export const useAddHolding = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ portfolioId, data }) => addHolding(portfolioId, data).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
    },
  });
};

export const useRemoveHolding = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ portfolioId, symbol }) => removeHolding(portfolioId, symbol).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
    },
  });
};