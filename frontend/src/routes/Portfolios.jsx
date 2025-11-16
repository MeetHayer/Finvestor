import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import { motion } from 'framer-motion';
import { Plus, Briefcase, Trash2, TrendingUp, TrendingDown, Calendar, DollarSign } from 'lucide-react';
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

// Helper function to get current price for a symbol
const getCurrentPrice = async (symbol) => {
  try {
    const response = await fetch(`/api/data/${symbol}?range_days=2`);
    const data = await response.json();
    return data?.latest?.close || 0;
  } catch (error) {
    console.warn(`Failed to fetch current price for ${symbol}:`, error);
    return 0;
  }
};

// Helper function to get historical price for a symbol on a specific date
const getHistoricalPrice = async (symbol, date) => {
  try {
    const response = await fetch(`/api/data/${symbol}?range_days=365`);
    const data = await response.json();
    if (data?.ohlc) {
      // Find the price data for the specific date
      const targetDate = new Date(date).toISOString().split('T')[0];
      const priceData = data.ohlc.find(price => {
        const priceDate = new Date(price[0]).toISOString().split('T')[0];
        return priceDate === targetDate;
      });
      if (priceData) {
        // Return (high + low) / 2
        return (priceData[2] + priceData[3]) / 2; // [timestamp, open, high, low, close, volume]
      }
    }
    return 0;
  } catch (error) {
    console.warn(`Failed to fetch historical price for ${symbol} on ${date}:`, error);
    return 0;
  }
};

// Helper function to calculate current portfolio value with live prices
const calculateCurrentPortfolioValue = async (holdings) => {
  if (!holdings || !Array.isArray(holdings)) return 0;
  
  let totalValue = 0;
  for (const holding of holdings) {
    const currentPrice = await getCurrentPrice(holding.symbol);
    const value = (holding.qty || 0) * currentPrice;
    totalValue += value;
  }
  
  return totalValue;
};

export default function Portfolios() {
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedPortfolio, setSelectedPortfolio] = useState(null);
  const [showAddHolding, setShowAddHolding] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState('');
  const [showSellModal, setShowSellModal] = useState(false);
  const [sellData, setSellData] = useState({ portfolioId: '', symbol: '', maxQty: 0 });
  const [expanded, setExpanded] = useState(null); // portfolioId or null

  const { data: portfolios = [], isLoading, refetch } = usePortfolios();
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
    // Frontend validation: require selected ticker, valid date, and positive shares
    if (!selectedTicker) {
      toast.error('Please select a ticker');
      return;
    }
    const sharesStr = formData.get('shares');
    const purchaseDate = formData.get('purchase_date');
    const sharesNum = parseFloat(sharesStr);
    if (!purchaseDate) {
      toast.error('Please select a purchase date');
      return;
    }
    if (!sharesStr || Number.isNaN(sharesNum) || sharesNum <= 0) {
      toast.error('Enter a valid positive number of shares');
      return;
    }

    const holdingData = {
      symbol: selectedTicker || formData.get('symbol'),
      qty: parseFloat(formData.get('shares')),
      // Let backend compute cost basis when null
      avg_cost: null,
      as_of: formData.get('purchase_date') || null,
    };

    try {
      const result = await addHoldingMutation.mutateAsync({ portfolioId: selectedPortfolio, data: holdingData });
      
      // Show success message with cost details
      const cost = result.total_cost || 0;
      const remainingCash = result.remaining_cash || 0;
      toast.success(
        `Added ${result.qty} shares of ${result.symbol} for $${cost.toLocaleString()}. Remaining cash: $${remainingCash.toLocaleString()}`
      );
      
      setShowAddHolding(false);
      setSelectedPortfolio(null);
      setSelectedTicker(''); // Reset selected ticker
      e.target.reset();
    } catch (error) {
      // Show specific error message
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to add holding';
      toast.error(errorMsg);
    }
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

  const handleSellHolding = async (portfolioId, symbol, fallbackQty) => {
    try {
      const res = await fetch(`/api/portfolios/${portfolioId}/holdings`);
      const rows = await res.json();
      const row = Array.isArray(rows) ? rows.find(r => r.symbol === symbol) : null;
      const qty = Number(row?.qty ?? fallbackQty ?? 0);
      setSellData({ portfolioId, symbol, maxQty: qty });
      try {
        const price = await getCurrentPrice(symbol);
        const el = document.getElementById('sell-price-preview');
        if (el) el.textContent = `$${Number(price).toFixed(2)}`;
      } catch {}
      setShowSellModal(true);
    } catch {
      setSellData({ portfolioId, symbol, maxQty: fallbackQty || 0 });
      setShowSellModal(true);
    }
  };

  const handleSellSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const qty = parseFloat(formData.get('qty'));

    if (qty > sellData.maxQty) {
      toast.error(`Cannot sell ${qty} shares, only ${sellData.maxQty} available`);
      return;
    }

    try {
      const response = await fetch(`/api/portfolios/${sellData.portfolioId}/holdings/${sellData.symbol}/sell`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ qty })
      });

      const result = await response.json();
      
      if (response.ok) {
        toast.success(`Sold ${result.sold_shares} shares for $${result.proceeds.toLocaleString()}`);
        // Force invalidate and refetch portfolios to reflect updated cash/holdings
        await queryClient.invalidateQueries({ queryKey: ['portfolios'] });
        await refetch();
        setShowSellModal(false);
      } else {
        toast.error(result.detail || 'Failed to sell holding');
      }
    } catch (error) {
      toast.error('Failed to sell holding');
    }
  };

  // Calculate current portfolio values when portfolios data changes
  useEffect(() => {
    if (portfolios && portfolios.length > 0) {
      portfolios.forEach(async (portfolio) => {
        try {
          // Fetch metrics from backend to ensure consistency
          const response = await fetch(`/api/portfolios/${portfolio.id}/metrics`);
          const metrics = await response.json();
          
          if (metrics) {
            // Calculate holdings value (current_value - cash)
            const holdingsValue = (metrics.current_value || 0) - (portfolio.cash || 0);
            
            // Update holdings value display
            const holdingsElement = document.getElementById(`holdings-value-${portfolio.id}`);
            if (holdingsElement) {
              holdingsElement.textContent = `$${holdingsValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            }
            
            // Update total value display
            const totalElement = document.getElementById(`current-value-${portfolio.id}`);
            if (totalElement) {
              totalElement.textContent = `$${(metrics.current_value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            }
            
            // Update HPR display using portfolio_return from metrics
            const hpr = metrics.portfolio_return || 0;
            const hprColor = hpr >= 0 ? 'text-green-600' : 'text-red-600';
            const hprSign = hpr >= 0 ? '+' : '';
            const hprElement = document.getElementById(`hpr-${portfolio.id}`);
            if (hprElement) {
              hprElement.textContent = `${hprSign}${hpr.toFixed(2)}%`;
              hprElement.className = `text-sm font-semibold ${hprColor}`;
            }
          }
        } catch (error) {
          console.error(`Failed to fetch metrics for portfolio ${portfolio.id}:`, error);
        }
      });
    }
  }, [portfolios]);

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
                    <div className="text-sm text-gray-500">Cash Balance</div>
                    <div className="font-semibold text-green-600">${(portfolio.cash || 0).toLocaleString()}</div>
                  </div>
                </div>

                <div className="border-t border-gray-200 pt-4 mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-500">Holdings Value</span>
                    <span className="text-sm font-semibold text-blue-600" id={`holdings-value-${portfolio.id}`}>
                      Loading...
                    </span>
                  </div>
                  
                  {/* Current Portfolio Value */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-500">Current Value</span>
                    <span className="text-sm font-semibold text-green-600" id={`current-value-${portfolio.id}`}>
                      Loading...
                    </span>
                  </div>
                  
                  {/* Holding Period Return */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-500">Holding Period Return</span>
                    <span className="text-sm font-semibold" id={`hpr-${portfolio.id}`}>
                      Loading...
                    </span>
                  </div>

                  {(portfolio.holdings || []).length > 0 ? (
                    <div className="space-y-2 max-h-32 overflow-y-auto">
                      {(portfolio.holdings || []).map((holding) => (
                        <div
                          key={holding.symbol}
                          className="flex items-center justify-between text-sm p-2 bg-gray-50 rounded"
                        >
                          <div className="flex items-center gap-2 flex-1">
                            <span className="font-medium">{holding.symbol}</span>
                            <span className="text-gray-500">×{holding.qty}</span>
                            <span className="text-xs text-gray-400 ml-auto">
                              @ ${(holding.avg_cost || 0).toFixed(2)}
                            </span>
                          </div>
                          <button
                            onClick={() => handleSellHolding(portfolio.id, holding.symbol, holding.qty)}
                            className="text-blue-600 hover:text-blue-800 text-xs font-medium px-2 py-1 rounded hover:bg-blue-50"
                          >
                            Sell
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-400 text-center py-2">
                      No holdings - All in cash (${(portfolio.cash || 0).toLocaleString()})
                    </p>
                  )}
                </div>

                {expanded === portfolio.id && (
                  <PerformancePanel portfolioId={portfolio.id} />
                )}
                <button className="btn-secondary w-full mt-3" onClick={() => setExpanded(expanded === portfolio.id ? null : portfolio.id)}>
                  {expanded === portfolio.id ? 'Hide Performance' : 'Show Performance'}
                </button>

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

      {/* Create Portfolio Modal - Enhanced UX */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="bg-white rounded-2xl shadow-2xl p-8 max-w-lg w-full"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 rounded-xl bg-primary-100 flex items-center justify-center">
                <Briefcase className="w-6 h-6 text-primary-600" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Create Portfolio</h2>
                <p className="text-sm text-gray-500">Track your investments and performance</p>
              </div>
            </div>

            <form onSubmit={handleCreate} className="space-y-5">
              {/* Portfolio Name */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Portfolio Name *
                </label>
                <input
                  type="text"
                  name="name"
                  required
                  autoFocus
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-all"
                  placeholder="e.g., Tech Growth, Dividend Stars"
                />
              </div>

              {/* Inception Date with Quick Select */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Start Date *
                </label>
                <div className="space-y-2">
                  <input
                    type="date"
                    name="inception_date"
                    required
                    defaultValue={new Date().toISOString().split('T')[0]}
                    max={new Date().toISOString().split('T')[0]}
                    onChange={(e) => {
                      // Auto-close picker after date selection
                      e.target.blur();
                      document.activeElement?.blur();
                    }}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-all"
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={(e) => {
                        const input = e.target.closest('form').querySelector('input[name="inception_date"]');
                        input.value = new Date().toISOString().split('T')[0];
                      }}
                      className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                    >
                      Today
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        const input = e.target.closest('form').querySelector('input[name="inception_date"]');
                        const date = new Date();
                        date.setDate(date.getDate() - 30);
                        input.value = date.toISOString().split('T')[0];
                      }}
                      className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                    >
                      1 Month Ago
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        const input = e.target.closest('form').querySelector('input[name="inception_date"]');
                        const date = new Date();
                        date.setFullYear(date.getFullYear() - 1);
                        input.value = date.toISOString().split('T')[0];
                      }}
                      className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                    >
                      1 Year Ago
                    </button>
                  </div>
                </div>
              </div>

              {/* Initial Cash */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Starting Cash (Optional)
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 font-medium">$</span>
                  <input
                    type="number"
                    name="initial_value"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    className="w-full pl-8 pr-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-all"
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">Leave blank if starting with $0 cash</p>
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Description (Optional)
                </label>
                <textarea
                  name="description"
                  rows="2"
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-all resize-none"
                  placeholder="Strategy, goals, notes..."
                />
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-4">
                <button 
                  type="submit" 
                  className="flex-1 bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 px-6 rounded-xl transition-all hover:shadow-lg hover:scale-[1.02] active:scale-[0.98]"
                >
                  Create Portfolio
                </button>
                <button 
                  type="button" 
                  onClick={() => setShowCreateModal(false)} 
                  className="px-6 py-3 border-2 border-gray-200 hover:border-gray-300 hover:bg-gray-50 text-gray-700 font-semibold rounded-xl transition-all"
                >
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
                  // 'required' on a custom component is not enforced by the browser; enforced in handleAddHolding
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
                  onChange={(e) => {
                    // Auto-close picker after date selection
                    e.target.blur();
                    document.activeElement?.blur();
                  }}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Cost basis will be set to (high + low) / 2 for this date
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
                <button type="submit" className="btn-primary flex-1" disabled={!selectedTicker}>
                  Add Holding
                </button>
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

      {/* Sell Holding Modal */}
      {showSellModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 rounded-xl bg-red-100 flex items-center justify-center">
                <TrendingDown className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Sell Shares</h2>
                <p className="text-sm text-gray-500">Sell {sellData.symbol} shares</p>
              </div>
            </div>

            <form onSubmit={handleSellSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Shares to Sell *
                </label>
                <input
                  type="number"
                  name="qty"
                  required
                  min="0.01"
                  max={sellData.maxQty}
                  step="0.01"
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition-all"
                  placeholder={`Max: ${sellData.maxQty} shares`}
                />
                <p className="text-xs text-gray-500 mt-1">
                  You own {sellData.maxQty} shares of {sellData.symbol}
                </p>
              </div>

              <div className="bg-gray-50 rounded-xl p-4">
                <div className="text-sm text-gray-600 mb-2">Sell Summary</div>
                <div className="text-sm">
                  <div className="flex justify-between">
                    <span>Shares to sell:</span>
                    <span id="sell-qty-preview">0</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Current price:</span>
                    <span id="sell-price-preview">Loading...</span>
                  </div>
                  <div className="flex justify-between font-semibold text-green-600 border-t pt-2 mt-2">
                    <span>Estimated proceeds:</span>
                    <span id="sell-proceeds-preview">$0.00</span>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <button 
                  type="submit" 
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-6 rounded-xl transition-all hover:shadow-lg hover:scale-[1.02] active:scale-[0.98]"
                >
                  Sell Shares
                </button>
                <button 
                  type="button" 
                  onClick={() => setShowSellModal(false)} 
                  className="px-6 py-3 border-2 border-gray-200 hover:border-gray-300 hover:bg-gray-50 text-gray-700 font-semibold rounded-xl transition-all"
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


function PerformancePanel({ portfolioId }) {
  const [series, setSeries] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showTx, setShowTx] = useState(false);
  const [tx, setTx] = useState([]);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [vs, mx] = await Promise.all([
          fetch(`/api/portfolios/${portfolioId}/value_series?days=365`).then(r => r.json()),
          fetch(`/api/portfolios/${portfolioId}/metrics`).then(r => r.json()),
        ]);
        if (!alive) return;
        setSeries(vs?.series || []);
        setMetrics(mx || null);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [portfolioId]);

  if (loading) return <div className="text-sm text-gray-500">Loading…</div>;

  const dates = series.map(p => new Date(p[0]).toISOString().slice(0,10));
  const values = series.map(p => p[1]);

  const option = {
    legend: { show: true },
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', scale: true },
    series: [{ name: 'Portfolio Value', type: 'line', data: values, smooth: true, showSymbol: false }]
  };

  const num = (x, d=4) => Number(x ?? 0).toFixed(d);

  return (
    <div className="mt-4 border rounded-lg p-3">
      <div className="h-56">
        <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
      </div>
      {metrics && (
        <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <div><span className="text-gray-500">Current Value:</span> <span className="font-semibold">${num(metrics.current_value, 2)}</span></div>
          <div><span className="text-gray-500">Portfolio Return:</span> <span className={`font-semibold ${(metrics.portfolio_return ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>{num(metrics.portfolio_return, 2)}%</span></div>
          <div><span className="text-gray-500">Gain/Loss:</span> <span className={`font-semibold ${(metrics.gain_loss ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>${num(metrics.gain_loss, 2)}</span></div>
        </div>
      )}
      <div className="mt-3">
        <button
          className="btn-secondary"
          onClick={async () => {
            if (!showTx) {
              try {
                const r = await fetch(`/api/portfolios/${portfolioId}/transactions`);
                const data = await r.json();
                setTx(Array.isArray(data) ? data : []);
              } catch {
                setTx([]);
              }
            }
            setShowTx(!showTx);
          }}
        >
          {showTx ? 'Hide Transactions' : 'View Transactions'}
        </button>
      </div>
      {showTx && (
        <div className="mt-3 border rounded-lg p-3 overflow-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500">
                <th className="pr-4">Date</th>
                <th className="pr-4">Side</th>
                <th className="pr-4">Symbol</th>
                <th className="pr-4">Qty</th>
                <th className="pr-4">Price</th>
                <th className="pr-4">Amount</th>
                <th className="pr-4">Remaining Cash</th>
              </tr>
            </thead>
            <tbody>
              {tx.length === 0 ? (
                <tr><td colSpan={6} className="text-gray-400">No transactions</td></tr>
              ) : tx.map((t) => (
                <tr key={t.id} className="border-t">
                  <td className="py-1 pr-4">{t.trade_date || (t.created_at ? String(t.created_at).slice(0,10) : '')}</td>
                  <td className="py-1 pr-4">{t.side}</td>
                  <td className="py-1 pr-4">{t.symbol}</td>
                  <td className="py-1 pr-4">{num(t.qty, 4)}</td>
                  <td className="py-1 pr-4">${num(t.price, 2)}</td>
                  <td className="py-1 pr-4">${num(t.amount, 2)}</td>
                  <td className="py-1 pr-4">${num(t.remaining_cash, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

