import { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, Briefcase, Trash2, TrendingUp, Calendar, DollarSign } from 'lucide-react';
import toast from 'react-hot-toast';
import { usePortfolios, useCreatePortfolio, useDeletePortfolio, useAddHolding, useRemoveHolding } from '../hooks/usePortfolios';
import { useTickerSearch } from '../lib/queries';
import TickerSearch from '../components/TickerSearch';

// Helper function to calculate portfolio value
const calculatePortfolioValue = (holdings) => {
  if (!holdings || !Array.isArray(holdings)) return 0;
  return holdings.reduce((total, holding) => {
    const value = (holding.qty || 0) * (holding.avg_cost || 0);
    return total + value;
  }, 0);
};

export default function Portfolios() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedPortfolio, setSelectedPortfolio] = useState(null);
  const [showAddHolding, setShowAddHolding] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState('');

  const { data: portfolios = [], isLoading } = usePortfolios();
  const createMutation = useCreatePortfolio();
  const deleteMutation = useDeletePortfolio();
  const addHoldingMutation = useAddHolding();
  const removeHoldingMutation = useRemoveHolding();

  const handleCreate = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    const portfolioData = {
      name: formData.get('name'),
      inception_date: formData.get('inception_date'),
      initial_value: parseFloat(formData.get('initial_value')) || 0,
    };

    toast.promise(
      createMutation.mutateAsync(portfolioData),
      {
        loading: 'Creating portfolio...',
        success: 'Portfolio created!',
        error: 'Failed to create portfolio',
      }
    );

    setShowCreateModal(false);
    e.target.reset();
  };

  const handleDelete = async (id, name) => {
    if (confirm(`Delete portfolio "${name}"?`)) {
      toast.promise(
        deleteMutation.mutateAsync(id),
        {
          loading: 'Deleting...',
          success: 'Portfolio deleted!',
          error: 'Failed to delete portfolio',
        }
      );
    }
  };

  const handleAddHolding = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    const holdingData = {
      symbol: selectedTicker || formData.get('symbol'), // Use selected ticker or form data
      qty: parseFloat(formData.get('shares')),
      avg_cost: 0, // Will be set by backend based on date
      as_of: formData.get('purchase_date') || null, // If date provided, backend will use open price
    };

    toast.promise(
      addHoldingMutation.mutateAsync({ portfolioId: selectedPortfolio, data: holdingData }),
      {
        loading: 'Adding holding...',
        success: 'Holding added with automatic pricing!',
        error: 'Failed to add holding',
      }
    );

    setShowAddHolding(false);
    setSelectedPortfolio(null);
    setSelectedTicker(''); // Reset selected ticker
    e.target.reset();
  };

  const handleRemoveHolding = async (portfolioId, symbol) => {
    if (confirm(`Remove ${symbol} from portfolio?`)) {
      toast.promise(
        removeHoldingMutation.mutateAsync({ portfolioId, symbol }),
        {
          loading: `Removing ${symbol}...`,
          success: `Removed ${symbol}!`,
          error: 'Failed to remove holding',
        }
      );
    }
  };

  const calculatePortfolioValue = (holdings) => {
    return holdings.reduce((sum, h) => sum + (h.shares * (h.average_cost || 0)), 0);
  };

  return (
    <div className="container mx-auto px-6 py-8">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-6"
      >
        <div>
          <h1 className="text-3xl font-bold">Portfolios</h1>
          <p className="text-gray-500 mt-1">Manage your investment portfolios</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          Create Portfolio
        </button>
      </motion.div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="shimmer h-64 rounded-lg"></div>
          ))}
        </div>
      ) : portfolios.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="card text-center py-12"
        >
          <Briefcase className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-700 mb-2">No portfolios yet</h3>
          <p className="text-gray-500 mb-4">Create your first portfolio to start tracking investments</p>
          <button onClick={() => setShowCreateModal(true)} className="btn-primary">
            Create Your First Portfolio
          </button>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {portfolios.map((portfolio, index) => {
            const portfolioValue = calculatePortfolioValue(portfolio.holdings);
            
            return (
              <motion.div
                key={portfolio.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.05 }}
                className="card hover:shadow-lg transition-shadow"
              >
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-xl font-bold text-gray-900">{portfolio.name}</h3>
                    {portfolio.description && (
                      <p className="text-sm text-gray-500 mt-1">{portfolio.description}</p>
                    )}
                  </div>
                  <button
                    onClick={() => handleDelete(portfolio.id, portfolio.name)}
                    className="text-red-500 hover:text-red-700 transition-colors"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <div className="text-sm text-gray-500">Inception</div>
                    <div className="font-semibold">{new Date(portfolio.inception_date).toLocaleDateString()}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Initial Value</div>
                    <div className="font-semibold">${portfolio.initial_value.toLocaleString()}</div>
                  </div>
                </div>

                <div className="border-t border-gray-200 pt-4 mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-500">Holdings ({(portfolio.holdings || []).length})</span>
                    <span className="text-sm font-semibold text-green-600">
                      ${portfolioValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  </div>

                  {(portfolio.holdings || []).length > 0 ? (
                    <div className="space-y-2 max-h-32 overflow-y-auto">
                      {(portfolio.holdings || []).map((holding) => (
                        <div
                          key={holding.symbol}
                          className="flex items-center justify-between text-sm p-2 bg-gray-50 rounded"
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{holding.symbol}</span>
                            <span className="text-gray-500">×{holding.qty}</span>
                          </div>
                          <button
                            onClick={() => handleRemoveHolding(portfolio.id, holding.symbol)}
                            className="text-red-500 hover:text-red-700 text-xs"
                          >
                            Remove
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-400 text-center py-2">No holdings yet</p>
                  )}
                </div>

                <button
                  onClick={() => {
                    setSelectedPortfolio(portfolio.id);
                    setShowAddHolding(true);
                  }}
                  className="btn-secondary w-full flex items-center justify-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  Add Holding
                </button>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Create Portfolio Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-xl p-6 max-w-md w-full"
          >
            <h2 className="text-2xl font-bold mb-4">Create Portfolio</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  name="name"
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
                  placeholder="e.g., Growth Portfolio"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Inception Date *
                </label>
                <input
                  type="date"
                  name="inception_date"
                  required
                  max={new Date().toISOString().split('T')[0]}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Initial Value ($)
                </label>
                <input
                  type="number"
                  name="initial_value"
                  step="0.01"
                  min="0"
                  defaultValue="0"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
                  placeholder="e.g., 10000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  name="description"
                  rows="2"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
                  placeholder="Optional description..."
                />
              </div>
              <div className="flex gap-2">
                <button type="submit" className="btn-primary flex-1">Create</button>
                <button type="button" onClick={() => setShowCreateModal(false)} className="btn-secondary flex-1">
                  Cancel
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

      {/* Add Holding Modal */}
      {showAddHolding && selectedPortfolio && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-xl p-6 max-w-md w-full"
          >
            <h2 className="text-2xl font-bold mb-4">Add Holding</h2>
            <form onSubmit={handleAddHolding} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Plus className="w-4 h-4 inline mr-1" />
                  Ticker Symbol *
                </label>
                <TickerSearch
                  placeholder="Search for stocks (e.g., AAPL, MSFT, GOOGL)..."
                  onSelect={(symbol) => {
                    setSelectedTicker(symbol);
                    toast.success(`Selected ${symbol}`);
                  }}
                  required
                />
                {selectedTicker && (
                  <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded">
                    <span className="text-green-800 font-medium">Selected: {selectedTicker}</span>
                  </div>
                )}
                <p className="text-xs text-gray-500 mt-1">
                  Select from your database of available stocks
                </p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Calendar className="w-4 h-4 inline mr-1" />
                  Purchase Date *
                </label>
                <input
                  type="date"
                  name="purchase_date"
                  required
                  max={new Date().toISOString().split('T')[0]}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Price will be automatically set to the open price on this date
                </p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <TrendingUp className="w-4 h-4 inline mr-1" />
                  Number of Shares *
                </label>
                <input
                  type="number"
                  name="shares"
                  required
                  step="0.01"
                  min="0.01"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
                  placeholder="e.g., 10"
                />
              </div>
              
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <div className="flex items-center gap-2 text-blue-800">
                  <DollarSign className="w-4 h-4" />
                  <span className="text-sm font-medium">Automatic Pricing</span>
                </div>
                <p className="text-xs text-blue-700 mt-1">
                  The purchase price will be automatically set to the opening price of the selected stock on the purchase date from our database.
                </p>
              </div>
              <div className="flex gap-2">
                <button type="submit" className="btn-primary flex-1">Add Holding</button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAddHolding(false);
                    setSelectedPortfolio(null);
                  }}
                  className="btn-secondary flex-1"
                >
                  Cancel
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </div>
  );
}


