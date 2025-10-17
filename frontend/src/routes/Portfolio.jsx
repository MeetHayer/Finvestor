import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Calendar, DollarSign, TrendingUp, Briefcase } from 'lucide-react';
import { usePortfolioById } from '../hooks/usePortfolioById';

// Skeleton loader for portfolio details
function PortfolioSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 bg-gray-200 rounded w-1/4"></div>
      <div className="h-6 bg-gray-200 rounded w-1/3"></div>
      <div className="h-64 bg-gray-200 rounded"></div>
    </div>
  );
}

// Empty state when no holdings
function EmptyState() {
  return (
    <div className="text-center py-12">
      <Briefcase className="w-16 h-16 text-gray-300 mx-auto mb-4" />
      <h3 className="text-lg font-medium text-gray-700 mb-2">No Holdings Yet</h3>
      <p className="text-gray-500">Add holdings from the Portfolios page</p>
    </div>
  );
}

export default function Portfolio() {
  const { id } = useParams();
  const { data: portfolio, isLoading, error } = usePortfolioById(id);

  if (isLoading) {
    return (
      <div className="container mx-auto px-6 py-8">
        <PortfolioSkeleton />
      </div>
    );
  }

  if (error || !portfolio) {
    return (
      <div className="container mx-auto px-6 py-8">
        <div className="card bg-red-50 border-red-200">
          <h3 className="text-red-700 font-semibold mb-2">Portfolio Not Found</h3>
          <p className="text-red-600 mb-4">
            {error?.message || 'This portfolio does not exist or has been deleted.'}
          </p>
          <Link to="/portfolios" className="btn-primary inline-flex items-center gap-2">
            <ArrowLeft className="w-4 h-4" />
            Back to Portfolios
          </Link>
        </div>
      </div>
    );
  }

  const holdings = portfolio.holdings || [];
  const totalValue = holdings.reduce((sum, h) => sum + (h.qty * h.avg_cost), 0);

  return (
    <div className="container mx-auto px-6 py-8 space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <Link 
            to="/portfolios" 
            className="text-sm text-gray-500 hover:text-primary-600 flex items-center gap-1 mb-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Portfolios
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">{portfolio.name}</h1>
        </div>
      </motion.div>

      {/* Portfolio Info Cards */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
      >
        {/* Inception Date */}
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
              <Calendar className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <div className="text-sm text-gray-500">Inception Date</div>
              <div className="text-lg font-bold text-gray-900">
                {new Date(portfolio.inception_date).toLocaleDateString()}
              </div>
            </div>
          </div>
        </div>

        {/* Initial Value */}
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-green-50 flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <div className="text-sm text-gray-500">Initial Value</div>
              <div className="text-lg font-bold text-gray-900">
                ${portfolio.initial_value?.toLocaleString() || '0'}
              </div>
            </div>
          </div>
        </div>

        {/* Current Holdings Value */}
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <div className="text-sm text-gray-500">Holdings Value</div>
              <div className="text-lg font-bold text-gray-900">
                ${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Holdings Table */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="card"
      >
        <h2 className="text-xl font-bold mb-4">Holdings</h2>
        
        {holdings.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Symbol
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Shares
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Avg Cost
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Value
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Added On
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {holdings.map((holding, index) => (
                  <tr key={index} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link 
                        to={`/ticker/${holding.symbol}`}
                        className="text-primary-600 hover:text-primary-700 font-medium"
                      >
                        {holding.symbol}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-gray-900">
                      {holding.qty?.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-gray-900">
                      ${holding.avg_cost?.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right font-medium text-gray-900">
                      ${(holding.qty * holding.avg_cost).toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-500">
                      {holding.as_of ? new Date(holding.as_of).toLocaleDateString() : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-gray-50">
                <tr>
                  <td colSpan="3" className="px-6 py-4 text-right font-bold text-gray-900">
                    Total Portfolio Value:
                  </td>
                  <td className="px-6 py-4 text-right font-bold text-gray-900">
                    ${totalValue.toFixed(2)}
                  </td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </motion.div>
    </div>
  );
}





