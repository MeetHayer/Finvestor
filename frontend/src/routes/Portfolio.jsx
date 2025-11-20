import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Calendar, DollarSign, TrendingUp, Briefcase, Activity, Shield, TrendingDown } from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import { useQuery } from '@tanstack/react-query';
import { usePortfolioById } from '../hooks/usePortfolioById';
import { usePortfolioRisk } from '../hooks/usePortfolioRisk';
import { getJSON } from '../lib/http';

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
  const { data: riskData, isLoading: riskLoading } = usePortfolioRisk(id);
  const [selectedBenchmark, setSelectedBenchmark] = useState(null); // null, 'SPY', 'QQQ', or 'DIA'
  const [benchmarkData, setBenchmarkData] = useState(null);

  // Fetch portfolio value series and metrics using React Query for automatic refetching
  const { data: valueSeriesData, isLoading: valueSeriesLoading } = useQuery({
    queryKey: ['portfolioValueSeries', id],
    queryFn: () => getJSON(`/portfolios/${id}/value_series?days=365`),
    enabled: Boolean(id),
    staleTime: 30 * 1000, // Consider stale after 30 seconds
    refetchOnWindowFocus: true, // Refetch when user returns to tab
  });

  const { data: metricsData, isLoading: metricsLoading } = useQuery({
    queryKey: ['portfolioMetrics', id],
    queryFn: () => getJSON(`/portfolios/${id}/metrics`),
    enabled: Boolean(id),
    staleTime: 30 * 1000, // Consider stale after 30 seconds
    refetchOnWindowFocus: true, // Refetch when user returns to tab
  });

  const valueSeries = valueSeriesData?.series || [];
  const metrics = metricsData || null;
  const chartLoading = valueSeriesLoading || metricsLoading;

  // Fetch benchmark data when selected
  useEffect(() => {
    if (!selectedBenchmark || !portfolio?.inception_date || valueSeries.length === 0) {
      setBenchmarkData(null);
      return;
    }

    const fetchBenchmark = async () => {
      try {
        // Get portfolio inception date and date range
        const portfolioStartDate = new Date(valueSeries[0][0]);
        const portfolioEndDate = new Date(valueSeries[valueSeries.length - 1][0]);
        const today = new Date();
        const daysDiff = Math.ceil((today - portfolioStartDate) / (1000 * 60 * 60 * 24));
        const daysToFetch = Math.max(daysDiff + 60, 730); // Fetch 2 years of data to ensure coverage

        const response = await fetch(`/api/data/${selectedBenchmark}?range_days=${daysToFetch}`);
        const data = await response.json();

        if (data?.ohlc && data.ohlc.length > 0) {
          // Portfolio initial investment value (X in your formula)
          const X = valueSeries[0][1];
          
          // Convert benchmark OHLC to price series
          const benchmarkPrices = data.ohlc
            .map(candle => ({
              date: new Date(candle[0]),
              close: candle[4]
            }))
            .filter(item => item.date >= portfolioStartDate); // Only include dates from inception onward

          if (benchmarkPrices.length === 0) {
            console.warn('No benchmark data available for portfolio date range');
            setBenchmarkData(null);
            return;
          }

          // Find benchmark price on or closest to portfolio inception date (M in your formula)
          const M = benchmarkPrices.reduce((closest, current) => {
            const closestDiff = Math.abs(closest.date.getTime() - portfolioStartDate.getTime());
            const currentDiff = Math.abs(current.date.getTime() - portfolioStartDate.getTime());
            return currentDiff < closestDiff ? current : closest;
          }).close;

          // For each day: value = X * N / M (where N is benchmark price on that day)
          const normalized = benchmarkPrices.map(item => ({
            date: item.date.toISOString().slice(0, 10),
            value: (X * item.close) / M
          }));

          setBenchmarkData({
            symbol: selectedBenchmark,
            series: normalized,
            initialPrice: M
          });
        }
      } catch (err) {
        console.error('Failed to fetch benchmark:', err);
        setBenchmarkData(null);
      }
    };

    fetchBenchmark();
  }, [selectedBenchmark, portfolio, valueSeries]);

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

      {/* Portfolio Value Chart */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.12 }}
        className="card"
      >
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <h2 className="text-xl font-bold text-gray-900">Portfolio Value Over Time</h2>
          
          {/* Benchmark Toggle Buttons */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-gray-600 mr-1">Compare with:</span>
            <button
              onClick={() => setSelectedBenchmark(null)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                selectedBenchmark === null
                  ? 'bg-gray-700 text-white shadow-md'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              None
            </button>
            <button
              onClick={() => setSelectedBenchmark('SPY')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                selectedBenchmark === 'SPY'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'bg-blue-50 text-blue-600 hover:bg-blue-100'
              }`}
            >
              SPY (S&P 500)
            </button>
            <button
              onClick={() => setSelectedBenchmark('QQQ')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                selectedBenchmark === 'QQQ'
                  ? 'bg-green-600 text-white shadow-md'
                  : 'bg-green-50 text-green-600 hover:bg-green-100'
              }`}
            >
              QQQ (Nasdaq)
            </button>
            <button
              onClick={() => setSelectedBenchmark('DIA')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                selectedBenchmark === 'DIA'
                  ? 'bg-purple-600 text-white shadow-md'
                  : 'bg-purple-50 text-purple-600 hover:bg-purple-100'
              }`}
            >
              DIA (Dow Jones)
            </button>
          </div>
        </div>
        
        {chartLoading ? (
          <div className="h-72 flex items-center justify-center bg-gray-50 rounded-lg">
            <div className="text-gray-400">Loading chart...</div>
          </div>
        ) : valueSeries.length > 0 ? (
          <>
            <div className="h-96">
              <ReactECharts
                option={{
                  animation: true,
                  backgroundColor: '#ffffff',
                  
                  // Interactive Data Zoom
                  dataZoom: [
                    {
                      type: 'inside', // Mouse wheel zoom
                      xAxisIndex: 0,
                      start: 0,
                      end: 100,
                      zoomOnMouseWheel: true,
                      moveOnMouseMove: true,
                      moveOnMouseWheel: false
                    },
                    {
                      type: 'slider', // Bottom slider
                      xAxisIndex: 0,
                      start: 0,
                      end: 100,
                      bottom: 10,
                      height: 25,
                      handleSize: '80%',
                      handleStyle: {
                        color: '#3b82f6',
                        borderColor: '#1d4ed8'
                      },
                      textStyle: { color: '#666', fontSize: 11 },
                      borderColor: '#ddd',
                      fillerColor: 'rgba(59, 130, 246, 0.2)',
                      dataBackground: {
                        lineStyle: { color: '#3b82f6' },
                        areaStyle: { color: 'rgba(59, 130, 246, 0.1)' }
                      }
                    }
                  ],
                  
                  // Enhanced Tooltip
                  tooltip: { 
                    trigger: 'axis',
                    axisPointer: {
                      type: 'cross',
                      crossStyle: { color: '#999' },
                      lineStyle: { color: '#999', width: 1, type: 'dashed' }
                    },
                    backgroundColor: 'rgba(0, 0, 0, 0.9)',
                    borderColor: '#333',
                    borderWidth: 1,
                    textStyle: { color: '#fff', fontSize: 13 },
                    formatter: (params) => {
                      if (!params || !params[0]) return '';
                      
                      const date = params[0].axisValue;
                      const portfolioValue = params[0].data;
                      const dataIndex = params[0].dataIndex;
                      
                      // Calculate daily change if not first day
                      let dailyChange = '';
                      if (dataIndex > 0) {
                        const prevValue = valueSeries[dataIndex - 1][1];
                        const change = portfolioValue - prevValue;
                        const changePct = (change / prevValue) * 100;
                        const changeColor = change >= 0 ? '#10b981' : '#ef4444';
                        const changeSign = change >= 0 ? '+' : '';
                        
                        dailyChange = `
                          <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #555;">
                            <span style="color: #aaa;">Daily Change:</span> 
                            <span style="color: ${changeColor}; font-weight: bold;">
                              ${changeSign}$${Math.abs(change).toFixed(2)} (${changeSign}${changePct.toFixed(2)}%)
                            </span>
                          </div>
                        `;
                      }
                      
                      // Calculate total return from inception
                      const initialValue = valueSeries[0][1];
                      const totalReturn = ((portfolioValue - initialValue) / initialValue) * 100;
                      const returnColor = totalReturn >= 0 ? '#10b981' : '#ef4444';
                      const returnSign = totalReturn >= 0 ? '+' : '';
                      
                      // Benchmark comparison (if active)
                      let benchmarkSection = '';
                      if (benchmarkData && params.length > 1 && params[1]) {
                        const benchmarkValue = params[1].data;
                        if (benchmarkValue !== null && benchmarkValue !== undefined) {
                          const benchInitial = benchmarkData.series[0].value;
                          const benchReturn = ((benchmarkValue - benchInitial) / benchInitial) * 100;
                          const benchColor = benchReturn >= 0 ? '#10b981' : '#ef4444';
                          const benchSign = benchReturn >= 0 ? '+' : '';
                          
                          const outperformance = totalReturn - benchReturn;
                          const outColor = outperformance >= 0 ? '#10b981' : '#ef4444';
                          const outSign = outperformance >= 0 ? '+' : '';
                          
                          benchmarkSection = `
                            <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #555;">
                              <span style="color: #aaa;">${benchmarkData.symbol} Return:</span> 
                              <span style="color: ${benchColor}; font-weight: bold;">
                                ${benchSign}${benchReturn.toFixed(2)}%
                              </span>
                            </div>
                            <div style="margin-top: 4px; padding: 6px; background: rgba(255,255,255,0.1); border-radius: 4px;">
                              <span style="color: #aaa;">Outperformance:</span> 
                              <span style="color: ${outColor}; font-weight: bold; font-size: 15px;">
                                ${outSign}${Math.abs(outperformance).toFixed(2)}%
                              </span>
                              ${outperformance >= 0 ? ' 🎯' : ' 📉'}
                            </div>
                          `;
                        }
                      }
                      
                      return `
                        <div style="font-weight: bold; margin-bottom: 8px; color: #fff; border-bottom: 1px solid #555; padding-bottom: 4px;">
                          ${date}
                        </div>
                        <div style="margin: 6px 0;">
                          <span style="color: #aaa;">Portfolio Value:</span><br/>
                          <span style="color: #fff; font-size: 18px; font-weight: bold;">$${Number(portfolioValue).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                        </div>
                        ${dailyChange}
                        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #555;">
                          <span style="color: #aaa;">Portfolio Return:</span> 
                          <span style="color: ${returnColor}; font-weight: bold;">
                            ${returnSign}${totalReturn.toFixed(2)}%
                          </span>
                        </div>
                        ${benchmarkSection}
                        <div style="margin-top: 8px; font-size: 10px; color: #888;">
                          📊 Day ${dataIndex + 1} of ${valueSeries.length}
                        </div>
                      `;
                    }
                  },
                  
                  // Legend
                  legend: { 
                    show: true,
                    top: 10,
                    textStyle: { fontSize: 13, color: '#374151' }
                  },
                  
                  // Grid Layout
                  grid: { left: 70, right: 50, top: 50, bottom: 80 },
                  
                  // X Axis
                  xAxis: { 
                    type: 'category', 
                    data: valueSeries.map(p => new Date(p[0]).toISOString().slice(0, 10)),
                    axisLabel: { 
                      rotate: 45, 
                      fontSize: 11,
                      color: '#6b7280'
                    },
                    axisLine: { lineStyle: { color: '#d1d5db' } },
                    splitLine: { show: false }
                  },
                  
                  // Y Axis
                  yAxis: { 
                    type: 'value', 
                    scale: true,
                    axisLabel: { 
                      formatter: (val) => `$${val.toLocaleString()}`,
                      fontSize: 11,
                      color: '#6b7280'
                    },
                    axisLine: { lineStyle: { color: '#d1d5db' } },
                    splitLine: { 
                      show: true,
                      lineStyle: { color: '#f3f4f6', type: 'dashed' }
                    }
                  },
                  
                  // Series
                  series: [
                    // Portfolio Value Series
                    {
                      name: 'Portfolio Value',
                      type: 'line',
                      data: valueSeries.map(p => p[1]),
                      smooth: true,
                      showSymbol: false,
                      symbol: 'circle',
                      symbolSize: 8,
                      lineStyle: { width: 3, color: '#3b82f6' },
                      itemStyle: { color: '#3b82f6' },
                      emphasis: {
                        focus: 'series',
                        itemStyle: {
                          color: '#1d4ed8',
                          borderColor: '#fff',
                          borderWidth: 2,
                          shadowBlur: 10,
                          shadowColor: 'rgba(59, 130, 246, 0.5)'
                        }
                      },
                      areaStyle: selectedBenchmark ? undefined : { 
                        color: {
                          type: 'linear',
                          x: 0, y: 0, x2: 0, y2: 1,
                          colorStops: [
                            { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
                            { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
                          ]
                        }
                      },
                      z: 2
                    },
                    // Benchmark Series (conditional)
                    ...(benchmarkData ? [{
                      name: `${benchmarkData.symbol} (If Invested at Inception)`,
                      type: 'line',
                      data: (() => {
                        // Create a map of benchmark dates to values for fast lookup
                        const benchmarkMap = new Map(
                          benchmarkData.series.map(item => [item.date, item.value])
                        );
                        
                        // For each portfolio date, find the closest benchmark value
                        return valueSeries.map(([portfolioDateStr, _]) => {
                          const portfolioDate = new Date(portfolioDateStr).toISOString().slice(0, 10);
                          
                          // Try exact match first
                          if (benchmarkMap.has(portfolioDate)) {
                            return benchmarkMap.get(portfolioDate);
                          }
                          
                          // If no exact match, find the closest earlier date
                          const portfolioTime = new Date(portfolioDate).getTime();
                          let closestValue = null;
                          let closestDiff = Infinity;
                          
                          for (const [benchDate, benchValue] of benchmarkMap.entries()) {
                            const benchTime = new Date(benchDate).getTime();
                            const diff = portfolioTime - benchTime;
                            
                            // Only consider dates on or before portfolio date
                            if (diff >= 0 && diff < closestDiff) {
                              closestDiff = diff;
                              closestValue = benchValue;
                            }
                          }
                          
                          return closestValue;
                        });
                      })(),
                      smooth: true,
                      showSymbol: false,
                      symbol: 'circle',
                      symbolSize: 6,
                      lineStyle: { 
                        width: 2.5, 
                        color: selectedBenchmark === 'SPY' ? '#f59e0b' : 
                               selectedBenchmark === 'QQQ' ? '#10b981' : '#a855f7',
                        type: 'dashed'
                      },
                      itemStyle: { 
                        color: selectedBenchmark === 'SPY' ? '#f59e0b' : 
                               selectedBenchmark === 'QQQ' ? '#10b981' : '#a855f7'
                      },
                      emphasis: {
                        focus: 'series',
                        itemStyle: {
                          borderColor: '#fff',
                          borderWidth: 2
                        }
                      },
                      connectNulls: true, // Connect line even if some dates are missing
                      z: 1
                    }] : [])
                  ]
                }}
                style={{ height: '100%', width: '100%' }}
                opts={{ renderer: 'canvas' }}
              />
            </div>
            
            {/* Chart Controls Help */}
            <div className="mt-3 flex items-center justify-between gap-4 text-xs flex-wrap">
              <div className="flex items-center gap-1 text-gray-500">
                <span className="font-semibold">💡 Tip:</span>
                <span>Scroll to zoom • Drag to pan • Hover for details</span>
              </div>
              
              {selectedBenchmark && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 text-blue-800">
                  <span className="font-semibold">📈 Benchmark Comparison:</span> Shows how your initial ${valueSeries[0]?.[1].toFixed(0)} 
                  would have performed if invested in <strong>{selectedBenchmark}</strong> on your portfolio inception date.
                </div>
              )}
            </div>
            
            {/* Performance Metrics Row */}
            {metrics && (
              <div className="mt-4 pt-4 border-t grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Current Value:</span>{' '}
                  <span className="font-semibold text-gray-900">
                    ${Number(metrics.current_value || 0).toFixed(2)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Portfolio Return:</span>{' '}
                  <span className={`font-semibold ${(metrics.portfolio_return || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {Number(metrics.portfolio_return || 0).toFixed(2)}%
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Gain/Loss:</span>{' '}
                  <span className={`font-semibold ${(metrics.gain_loss || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    ${Number(metrics.gain_loss || 0).toFixed(2)}
                  </span>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="h-72 flex items-center justify-center bg-gray-50 rounded-lg">
            <div className="text-center text-gray-500">
              <TrendingUp className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p>No performance data yet</p>
              <p className="text-xs mt-1">Add transactions to see your portfolio grow!</p>
            </div>
          </div>
        )}
      </motion.div>

      {/* Risk Metrics Section */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.15 }}
      >
        <h2 className="text-xl font-bold text-gray-900 mb-3">Risk Metrics</h2>
        
        {riskLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="card animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-20 mb-2"></div>
                <div className="h-6 bg-gray-200 rounded w-16"></div>
              </div>
            ))}
          </div>
        ) : riskData?.metrics ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Volatility */}
            <div className="card bg-gradient-to-br from-blue-50 to-white border-blue-100">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
                  <Activity className="w-4 h-4 text-blue-600" />
                </div>
                <div className="text-sm font-medium text-gray-600">Volatility (Annual)</div>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {riskData.metrics.volatility_annual !== null
                  ? `${(riskData.metrics.volatility_annual * 100).toFixed(2)}%`
                  : 'N/A'}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Standard deviation of returns
              </div>
            </div>

            {/* Sharpe Ratio */}
            <div className="card bg-gradient-to-br from-green-50 to-white border-green-100">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center">
                  <TrendingUp className="w-4 h-4 text-green-600" />
                </div>
                <div className="text-sm font-medium text-gray-600">Sharpe Ratio</div>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {riskData.metrics.sharpe !== null
                  ? riskData.metrics.sharpe.toFixed(2)
                  : 'N/A'}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Risk-adjusted return
              </div>
            </div>

            {/* Max Drawdown */}
            <div className="card bg-gradient-to-br from-orange-50 to-white border-orange-100">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-lg bg-orange-100 flex items-center justify-center">
                  <TrendingDown className="w-4 h-4 text-orange-600" />
                </div>
                <div className="text-sm font-medium text-gray-600">Max Drawdown</div>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {riskData.metrics.max_drawdown_pct !== null
                  ? `-${riskData.metrics.max_drawdown_pct.toFixed(2)}%`
                  : 'N/A'}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Worst peak-to-trough decline
              </div>
            </div>

            {/* VaR */}
            <div className="card bg-gradient-to-br from-red-50 to-white border-red-100">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-lg bg-red-100 flex items-center justify-center">
                  <Shield className="w-4 h-4 text-red-600" />
                </div>
                <div className="text-sm font-medium text-gray-600">VaR (95%, 1-day)</div>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {riskData.metrics.var_95_amount !== null
                  ? `$${riskData.metrics.var_95_amount.toFixed(0)}`
                  : 'N/A'}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {riskData.metrics.var_95_pct !== null
                  ? `${riskData.metrics.var_95_pct.toFixed(2)}% of portfolio`
                  : 'Historical Value-at-Risk'}
              </div>
            </div>
          </div>
        ) : (
          <div className="card bg-yellow-50 border-yellow-200">
            <p className="text-sm text-yellow-800">
              {riskData?.metrics?.message || 'Risk metrics unavailable. Add transactions to calculate risk.'}
            </p>
          </div>
        )}

        {/* Risk Metrics Explanations */}
        {riskData?.metrics && !riskData.metrics.message && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.25 }}
            className="mt-6 card bg-gray-50"
          >
            <h3 className="text-lg font-bold text-gray-900 mb-4">📊 How These Metrics Are Calculated</h3>
            
            <div className="space-y-4 text-sm text-gray-700">
              {/* Volatility */}
              <div className="border-l-4 border-blue-400 pl-4">
                <h4 className="font-semibold text-blue-900 mb-1">Volatility (Annualized)</h4>
                <p className="mb-2">
                  Measures the dispersion of your portfolio's daily returns, expressed as an annualized percentage.
                  <strong> Higher volatility = larger price swings</strong> (both up and down).
                </p>
                <div className="bg-white rounded p-2 font-mono text-xs mb-2">
                  σ<sub>annual</sub> = σ<sub>daily</sub> × √252
                </div>
                <p className="text-xs text-gray-600 mb-2">
                  <strong>Your Portfolio:</strong> {(riskData.metrics.volatility_annual * 100).toFixed(2)}%
                </p>
                <div className="bg-blue-50 rounded p-2 text-xs">
                  <p className="font-semibold text-blue-900 mb-1">📊 Typical Ranges:</p>
                  <ul className="space-y-0.5 text-blue-800">
                    <li>• <strong>&lt;10%:</strong> Very low risk (bonds, stable stocks)</li>
                    <li>• <strong>10-20%:</strong> Low to moderate risk (diversified portfolios, S&P 500 ~15%)</li>
                    <li>• <strong>20-30%:</strong> Moderate to high risk (growth stocks, sector-focused)</li>
                    <li>• <strong>&gt;30%:</strong> High risk (individual tech stocks, crypto)</li>
                  </ul>
                </div>
              </div>

              {/* Sharpe Ratio */}
              <div className="border-l-4 border-green-400 pl-4">
                <h4 className="font-semibold text-green-900 mb-1">Sharpe Ratio</h4>
                <p className="mb-2">
                  Measures <strong>risk-adjusted return</strong>: how much excess return you earn per unit of risk.
                  <strong> Higher is better</strong> - it means you're getting more return for each unit of risk taken.
                </p>
                <div className="bg-white rounded p-2 font-mono text-xs mb-2">
                  Sharpe = (R<sub>portfolio</sub> - R<sub>risk-free</sub>) / σ<sub>portfolio</sub>
                </div>
                {riskData.metrics.sharpe !== null ? (
                  <>
                    <p className="text-xs text-gray-600 mb-2">
                      <strong>Your Portfolio:</strong> {riskData.metrics.sharpe.toFixed(2)}
                    </p>
                    <div className="bg-green-50 rounded p-2 text-xs">
                      <p className="font-semibold text-green-900 mb-1">📊 Industry Interpretation:</p>
                      <ul className="space-y-0.5 text-green-800">
                        <li>• <strong>&lt;0:</strong> ❌ Losing money relative to risk-free rate (T-Bills)</li>
                        <li>• <strong>0 to 1:</strong> ⚠️ Suboptimal - barely beating risk-free rate for risk taken</li>
                        <li>• <strong>1 to 2:</strong> ✅ Good - solid risk-adjusted returns</li>
                        <li>• <strong>2 to 3:</strong> 🌟 Very Good - strong performance (top quartile)</li>
                        <li>• <strong>&gt;3:</strong> 🚀 Excellent - exceptional (top 10%, rare to sustain)</li>
                      </ul>
                      <p className="mt-2 text-green-700 font-medium">
                        {riskData.metrics.sharpe > 3 && '🚀 Outstanding! Your portfolio is in the top tier.'}
                        {riskData.metrics.sharpe > 2 && riskData.metrics.sharpe <= 3 && '🌟 Excellent risk-adjusted performance!'}
                        {riskData.metrics.sharpe > 1 && riskData.metrics.sharpe <= 2 && '✅ Solid returns for the risk taken.'}
                        {riskData.metrics.sharpe > 0 && riskData.metrics.sharpe <= 1 && '⚠️ Consider improving returns or reducing volatility.'}
                        {riskData.metrics.sharpe <= 0 && '❌ Portfolio is underperforming T-Bills - reassess strategy.'}
                      </p>
                    </div>
                  </>
                ) : (
                  <p className="text-xs text-yellow-700 bg-yellow-50 p-2 rounded">
                    <strong>N/A:</strong> Sharpe ratio requires risk-free rate data (3-month T-Bill from FRED). 
                    The <code className="bg-white px-1 rounded">risk_free_series</code> table is currently empty. 
                    Other metrics still provide valuable risk insights!
                  </p>
                )}
              </div>

              {/* Max Drawdown */}
              <div className="border-l-4 border-orange-400 pl-4">
                <h4 className="font-semibold text-orange-900 mb-1">Max Drawdown</h4>
                <p className="mb-2">
                  The largest peak-to-trough decline in portfolio value during the period.
                  <strong> Lower (smaller) is better</strong> - it means your portfolio's worst losses were more contained.
                </p>
                <div className="bg-white rounded p-2 font-mono text-xs mb-2">
                  Max DD = (Trough Value - Peak Value) / Peak Value
                </div>
                <p className="text-xs text-gray-600 mb-2">
                  <strong>Your Portfolio:</strong> -{riskData.metrics.max_drawdown_pct.toFixed(2)}%
                </p>
                <div className="bg-orange-50 rounded p-2 text-xs">
                  <p className="font-semibold text-orange-900 mb-1">📊 Risk Assessment:</p>
                  <ul className="space-y-0.5 text-orange-800">
                    <li>• <strong>&lt;5%:</strong> 🟢 Excellent - very stable (rare, usually bonds)</li>
                    <li>• <strong>5-10%:</strong> ✅ Good - well-controlled risk</li>
                    <li>• <strong>10-20%:</strong> ⚠️ Moderate - typical for balanced portfolios (S&P 500 ~15-20% in calm years)</li>
                    <li>• <strong>20-30%:</strong> 🟡 High - significant drawdowns (aggressive growth)</li>
                    <li>• <strong>&gt;30%:</strong> 🔴 Very High - severe losses (individual stocks, bear markets)</li>
                  </ul>
                  <p className="mt-2 text-orange-700 font-medium">
                    💡 <strong>What this means:</strong> At your worst point, you experienced a{' '}
                    {riskData.metrics.max_drawdown_pct.toFixed(2)}% decline from your peak portfolio value.
                    {riskData.metrics.max_drawdown_pct < 10 && ' This shows strong downside protection!'}
                    {riskData.metrics.max_drawdown_pct >= 10 && riskData.metrics.max_drawdown_pct < 20 && ' This is typical for equity portfolios.'}
                    {riskData.metrics.max_drawdown_pct >= 20 && ' Consider diversification to reduce future drawdowns.'}
                  </p>
                </div>
              </div>

              {/* VaR */}
              <div className="border-l-4 border-red-400 pl-4">
                <h4 className="font-semibold text-red-900 mb-1">Value-at-Risk (VaR 95%, 1-day)</h4>
                <p className="mb-2">
                  Estimates the maximum loss expected over 1 day with 95% confidence using historical returns.
                  <strong> Lower VaR = more predictable</strong> daily losses.
                </p>
                <div className="bg-white rounded p-2 font-mono text-xs mb-2">
                  VaR = 5th percentile of daily returns × portfolio value
                </div>
                <p className="text-xs text-gray-600 mb-2">
                  <strong>Your Portfolio:</strong> ${riskData.metrics.var_95_amount?.toFixed(2) || 'N/A'} ({riskData.metrics.var_95_pct?.toFixed(2) || 'N/A'}%)
                </p>
                <div className="bg-red-50 rounded p-2 text-xs">
                  <p className="font-semibold text-red-900 mb-1">📊 What This Means:</p>
                  <p className="text-red-800 mb-2">
                    On <strong>95% of trading days</strong>, your portfolio should <strong>not lose more than</strong> this amount.
                    However, on roughly <strong>1 out of every 20 days</strong> (5%), losses could exceed this threshold.
                  </p>
                  <p className="font-semibold text-red-900 mb-1">💡 Practical Example:</p>
                  <p className="text-red-800">
                    If your VaR is ${riskData.metrics.var_95_amount?.toFixed(0) || 0}, this means:
                  </p>
                  <ul className="mt-1 space-y-0.5 text-red-800">
                    <li>• <strong>Most days:</strong> Losses will be less than this amount</li>
                    <li>• <strong>~1 day per month:</strong> Losses could exceed this amount</li>
                    <li>• <strong>Extreme events:</strong> "Black swan" days (2008 crash, COVID) can far exceed VaR</li>
                  </ul>
                  <p className="mt-2 text-red-700 font-medium bg-red-100 p-1 rounded">
                    ⚠️ <strong>Important:</strong> VaR is <em>not</em> a ceiling - extreme events (tail risks) can and do happen!
                  </p>
                </div>
              </div>

              {/* Data Info */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mt-4">
                <p className="text-xs text-blue-800">
                  <strong>📈 Data Used:</strong> These metrics are calculated from {riskData.metrics.num_observations} daily portfolio value observations 
                  reconstructed from your transaction history since inception.
                  {riskData.metrics.num_observations < 50 && ' (Note: More data will improve VaR accuracy)'}
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </motion.div>

      {/* Holdings Table */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
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





