import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Plus, Star, Trash2, TrendingUp } from 'lucide-react';
import toast from 'react-hot-toast';
import { useWatchlists, useCreateWatchlist, useDeleteWatchlist, useAddToWatchlist, useRemoveFromWatchlist } from '../lib/queries';
import TickerSearch from '../components/TickerSearch';

export default function Watchlists() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedWatchlist, setSelectedWatchlist] = useState(null);
  const [showAddTicker, setShowAddTicker] = useState(false);

  const { data: watchlists = [], isLoading } = useWatchlists();
  const createMutation = useCreateWatchlist();
  const deleteMutation = useDeleteWatchlist();
  const addTickerMutation = useAddToWatchlist();
  const removeTickerMutation = useRemoveFromWatchlist();

  const handleCreate = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const name = formData.get('name');

    toast.promise(
      createMutation.mutateAsync({ name }),
      {
        loading: 'Creating watchlist...',
        success: 'Watchlist created!',
        error: 'Failed to create watchlist',
      }
    );

    setShowCreateModal(false);
    e.target.reset();
  };

  const handleDelete = async (id, name) => {
    if (confirm(`Delete watchlist "${name}"?`)) {
      toast.promise(
        deleteMutation.mutateAsync(id),
        {
          loading: 'Deleting...',
          success: 'Watchlist deleted!',
          error: 'Failed to delete watchlist',
        }
      );
    }
  };

  const handleAddTicker = async (watchlistId, symbol) => {
    toast.promise(
      addTickerMutation.mutateAsync({ watchlistId, symbol }),
      {
        loading: `Adding ${symbol}...`,
        success: `Added ${symbol} to watchlist!`,
        error: 'Failed to add ticker',
      }
    );
    setShowAddTicker(false);
    setSelectedWatchlist(null);
  };

  const handleRemoveTicker = async (watchlistId, symbol) => {
    toast.promise(
      removeTickerMutation.mutateAsync({ watchlistId, symbol }),
      {
        loading: `Removing ${symbol}...`,
        success: `Removed ${symbol}!`,
        error: 'Failed to remove ticker',
      }
    );
  };

  return (
    <div className="container mx-auto px-6 py-8">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-6"
      >
        <div>
          <h1 className="text-3xl font-bold">Watchlists</h1>
          <p className="text-gray-500 mt-1">Track your favorite stocks</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          Create Watchlist
        </button>
      </motion.div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="shimmer h-48 rounded-lg"></div>
          ))}
        </div>
      ) : watchlists.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="card text-center py-12"
        >
          <Star className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-700 mb-2">No watchlists yet</h3>
          <p className="text-gray-500 mb-4">Create your first watchlist to start tracking stocks</p>
          <button onClick={() => setShowCreateModal(true)} className="btn-primary">
            Create Your First Watchlist
          </button>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {watchlists.map((watchlist, index) => (
            <motion.div
              key={watchlist.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.05 }}
              className="card hover:shadow-lg transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-xl font-bold text-gray-900">{watchlist.name}</h3>
                  {watchlist.description && (
                    <p className="text-sm text-gray-500 mt-1">{watchlist.description}</p>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(watchlist.id, watchlist.name)}
                  className="text-red-500 hover:text-red-700 transition-colors"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>

              <div className="flex items-center gap-2 text-gray-600 mb-4">
                <Star className="w-4 h-4" />
                <span className="text-sm">{watchlist.tickers?.length || 0} stocks</span>
              </div>

              <div className="space-y-2 mb-4">
                {watchlist.tickers && watchlist.tickers.length > 0 ? (
                  watchlist.tickers.slice(0, 5).map((ticker) => (
                    <div
                      key={ticker.symbol}
                      className="flex items-center justify-between p-2 bg-gray-50 rounded hover:bg-gray-100 transition-colors"
                    >
                      <Link
                        to={`/ticker/${ticker.symbol}`}
                        className="flex-1 flex items-center gap-2 hover:text-primary-600"
                      >
                        <TrendingUp className="w-4 h-4" />
                        <span className="font-medium">{ticker.symbol}</span>
                      </Link>
                      <button
                        onClick={() => handleRemoveTicker(watchlist.id, ticker.symbol)}
                        className="text-red-500 hover:text-red-700 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-400 text-center py-4">No tickers yet</p>
                )}
                {watchlist.ticker_count > 5 && (
                  <p className="text-xs text-gray-400 text-center">
                    and {watchlist.ticker_count - 5} more...
                  </p>
                )}
              </div>

              <button
                onClick={() => {
                  setSelectedWatchlist(watchlist.id);
                  setShowAddTicker(true);
                }}
                className="btn-secondary w-full flex items-center justify-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add Ticker
              </button>
            </motion.div>
          ))}
        </div>
      )}

      {/* Create Watchlist Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-xl p-6 max-w-md w-full"
          >
            <h2 className="text-2xl font-bold mb-4">Create Watchlist</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  name="name"
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                  placeholder="e.g., Tech Stocks"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  name="description"
                  rows="3"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                  placeholder="Optional description..."
                />
              </div>
              <div className="flex gap-2">
                <button type="submit" className="btn-primary flex-1">
                  Create
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="btn-secondary flex-1"
                >
                  Cancel
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

      {/* Add Ticker Modal */}
      {showAddTicker && selectedWatchlist && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-xl p-6 max-w-md w-full"
          >
            <h2 className="text-2xl font-bold mb-4">Add Ticker</h2>
            <TickerSearch
              placeholder="Search for a ticker..."
              className="mb-4"
              onSelect={(symbol) => handleAddTicker(selectedWatchlist, symbol)}
            />
            <button
              onClick={() => {
                setShowAddTicker(false);
                setSelectedWatchlist(null);
              }}
              className="btn-secondary w-full"
            >
              Cancel
            </button>
          </motion.div>
        </div>
      )}
    </div>
  );
}


