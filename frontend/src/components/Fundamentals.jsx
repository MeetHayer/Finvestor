import { TrendingUp, TrendingDown, DollarSign, Activity, BarChart } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Fundamentals({ data, loading }) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="shimmer h-20 rounded-lg"></div>
        ))}
      </div>
    );
  }

  if (!data) return null;

  const metrics = [
    {
      label: 'P/E Ratio (TTM)',
      value: (data.trailingPE || data.pe_ratio) ? (data.trailingPE || data.pe_ratio).toFixed(2) : 'N/A',
      icon: Activity,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
    },
    {
      label: 'Market Cap',
      value: (data.marketCap || data.market_cap) ? `$${((data.marketCap || data.market_cap) / 1e9).toFixed(2)}B` : 'N/A',
      icon: DollarSign,
      color: 'text-green-600',
      bg: 'bg-green-50',
    },
    {
      label: 'Beta',
      value: data.beta ? data.beta.toFixed(2) : 'N/A',
      icon: BarChart,
      color: 'text-purple-600',
      bg: 'bg-purple-50',
    },
    {
      label: '52-Week High',
      value: (data.fiftyTwoWeekHigh || data.week_52_high) ? `$${(data.fiftyTwoWeekHigh || data.week_52_high).toFixed(2)}` : 'N/A',
      icon: TrendingUp,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50',
    },
    {
      label: '52-Week Low',
      value: (data.fiftyTwoWeekLow || data.week_52_low) ? `$${(data.fiftyTwoWeekLow || data.week_52_low).toFixed(2)}` : 'N/A',
      icon: TrendingDown,
      color: 'text-red-600',
      bg: 'bg-red-50',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      {metrics.map((metric, index) => (
        <motion.div
          key={metric.label}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.05 }}
          className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow"
        >
          <div className={`w-10 h-10 rounded-lg ${metric.bg} flex items-center justify-center mb-3`}>
            <metric.icon className={`w-5 h-5 ${metric.color}`} />
          </div>
          <div className="text-sm text-gray-500 mb-1">{metric.label}</div>
          <div className="text-xl font-bold text-gray-900">{metric.value}</div>
        </motion.div>
      ))}
    </div>
  );
}



