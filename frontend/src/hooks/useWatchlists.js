/**
 * Watchlist management hooks
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  getWatchlists, 
  createWatchlist, 
  deleteWatchlist,
  addToWatchlist,
  removeFromWatchlist,
} from '../lib/api';

// Query: Get all watchlists
export const useWatchlists = () => {
  return useQuery({
    queryKey: ['watchlists'],
    queryFn: () => getWatchlists().then(r => r.data),
    staleTime: 2 * 60 * 1000,
  });
};

// Mutation: Create new watchlist
export const useCreateWatchlist = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data) => createWatchlist(data).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] });
    },
  });
};

// Mutation: Delete watchlist
export const useDeleteWatchlist = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (watchlistId) => deleteWatchlist(watchlistId).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] });
    },
  });
};

// Mutation: Add ticker to watchlist
export const useAddToWatchlist = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ watchlistId, symbol }) => addToWatchlist(watchlistId, symbol).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] });
    },
  });
};

// Mutation: Remove ticker from watchlist
export const useRemoveFromWatchlist = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ watchlistId, symbol }) => removeFromWatchlist(watchlistId, symbol).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] });
    },
  });
};

