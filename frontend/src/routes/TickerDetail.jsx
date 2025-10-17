import { useState, useMemo, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import { motion } from 'framer-motion';
import { Star, RefreshCw, TrendingUp, TrendingDown } from 'lucide-react';
import toast from 'react-hot-toast';
import { useSafeQuery as useQuery } from '../lib/querySafe';
import { getJSON } from '../lib/http';
import Fundamentals from '../components/Fundamentals';
import { ChartSkeleton } from '../components/LoadingSkeleton';
import TickerSearch from '../components/TickerSearch';

export default function TickerDetail() {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const [timeRange, setTimeRange] = useState(365);
  const [selectedTicker, setSelectedTicker] = useState(symbol || null);

  // Use React Query for data fetching with caching
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['marketData', selectedTicker, timeRange],
    queryFn: () => getJSON(`/data/${selectedTicker}?range_days=${timeRange}`),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    enabled: Boolean(selectedTicker && selectedTicker.trim().length > 0),
    retry: 2,
  });

  // Update URL when ticker changes
  useEffect(() => {
    if (selectedTicker && selectedTicker !== symbol) {
      navigate(`/ticker/${selectedTicker}`, { replace: true });
    }
  }, [selectedTicker, symbol, navigate]);

  const handleRefresh = async () => {
    const promise = refetch();
    toast.promise(promise, {
      loading: 'Refreshing data...',
      success: 'Data refreshed successfully!',
      error: 'Failed to refresh data',
    });
  };

  const handleTickerSelect = (selectedSymbol) => {
    setSelectedTicker(selectedSymbol);
    toast.success(`Switched to ${selectedSymbol}`);
  };

  // Filter prices based on time range (for proper date filtering)
  const filteredPrices = useMemo(() => {
    if (!data || !data.ohlc) return [];
    
    // Just return the last N days of data, don't filter by current date
    // since the data might have future dates or different timezones
    return data.ohlc.slice(-timeRange);
  }, [data?.ohlc, timeRange]);

  // Guard against missing data AFTER hooks
  if (!selectedTicker) {
    return (
      <div className="p-6 space-y-6">
        <h1 className="text-2xl font-semibold">Stock Analysis</h1>
        
        {/* Search Bar */}
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <h2 className="text-lg font-semibold mb-3">Search for a Stock</h2>
          <TickerSearch 
            placeholder="Search for stocks (e.g., AAPL, MSFT, GOOGL)..." 
            onSelect={handleTickerSelect}
          />
        </div>

        <div className="text-center py-12">
          <div className="text-gray-500 text-lg">
            Search for a stock above to view its chart and fundamentals
          </div>
        </div>
      </div>
    );
  }

  if (!data || !data.ohlc) {
    return (
      <div className="p-6 space-y-6">
        <h1 className="text-2xl font-semibold">Stock Analysis - {selectedTicker}</h1>
        
        {/* Search Bar */}
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <h2 className="text-lg font-semibold mb-3">Search for Another Stock</h2>
          <TickerSearch 
            placeholder="Search for stocks (e.g., AAPL, MSFT, GOOGL)..." 
            onSelect={handleTickerSelect}
          />
        </div>

        <div className="text-center py-12">
          <div className="text-gray-500 text-lg">Loading data for {selectedTicker}...</div>
        </div>
      </div>
    );
  }

  const getChartOption = () => {
    if (!filteredPrices || filteredPrices.length === 0) return {};

    // Keep data in chronological order (left to right: oldest to newest)
    const prices = filteredPrices.slice(); // No reverse - keep ASC order
    const dates = prices.map(p => new Date(p[0]).toISOString().split('T')[0]); // Convert timestamp to date string
    const ohlc = prices.map(p => [p[1], p[4], p[3], p[2]]); // [open, close, low, high] - CORRECT ORDER
    const volumes = prices.map(p => p[5]);

    return {
      animation: true,
      backgroundColor: '#ffffff',
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          crossStyle: {
            color: '#999'
          },
          lineStyle: {
            color: '#999',
            width: 1,
            type: 'dashed'
          }
        },
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderColor: '#333',
        textStyle: {
          color: '#fff'
        },
        formatter: function (params) {
          let result = `<div style="font-weight: bold; margin-bottom: 8px; color: #fff;">${params[0].axisValue}</div>`;
          params.forEach(param => {
            if (param.seriesName === selectedTicker) {
              const data = param.data;
              const isGreen = data[1] >= data[0]; // Close >= Open
              result += `
                <div style="margin: 4px 0;">
                  <span style="color: ${isGreen ? '#10b981' : '#ef4444'}; font-weight: bold;">●</span>
                  <span style="margin-left: 8px; color: #fff;">Open: $${data[0].toFixed(2)}</span><br/>
                  <span style="margin-left: 20px; color: #fff;">High: $${data[3].toFixed(2)}</span><br/>
                  <span style="margin-left: 20px; color: #fff;">Low: $${data[2].toFixed(2)}</span><br/>
                  <span style="margin-left: 20px; color: ${isGreen ? '#10b981' : '#ef4444'}; font-weight: bold;">Close: $${data[1].toFixed(2)}</span>
                </div>
              `;
            } else if (param.seriesName === 'Volume') {
              result += `
                <div style="margin: 4px 0;">
                  <span style="color: ${param.color}; font-weight: bold;">●</span>
                  <span style="margin-left: 8px; color: #fff;">Volume: ${param.data.toLocaleString()}</span>
                </div>
              `;
            }
          });
          return result;
        }
      },
      grid: [
        { left: '5%', right: '5%', height: '60%' },
        { left: '5%', right: '5%', top: '70%', height: '15%' }
      ],
      xAxis: [
        {
          type: 'category',
          data: dates,
          scale: true,
          boundaryGap: false,
          axisLine: { onZero: false },
          splitLine: { show: false },
          min: 'dataMin',
          max: 'dataMax'
        },
        {
          type: 'category',
          gridIndex: 1,
          data: dates,
          scale: true,
          boundaryGap: false,
          axisLine: { onZero: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          min: 'dataMin',
          max: 'dataMax'
        }
      ],
      yAxis: [
        {
          scale: true,
          splitArea: { show: true }
        },
        {
          scale: true,
          gridIndex: 1,
          splitNumber: 3,
          axisLabel: { 
            show: true,
            formatter: function(value) {
              if (value >= 1000000) {
                return (value / 1000000).toFixed(1) + 'M';
              } else if (value >= 1000) {
                return (value / 1000).toFixed(1) + 'K';
              }
              return value.toString();
            }
          },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false }
        }
      ],
      series: [
        {
          name: selectedTicker,
          type: 'candlestick',
          data: ohlc,
          itemStyle: {
            color: '#ef4444',
            color0: '#10b981',
            borderColor: '#ef4444',
            borderColor0: '#10b981',
            borderWidth: 1
          },
          emphasis: {
            itemStyle: {
              borderWidth: 2,
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.3)'
            }
          }
        },
        {
          name: 'Volume',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volumes,
          itemStyle: {
            color: function(params) {
              // Color volume bars based on price direction
              const candleIndex = params.dataIndex;
              if (candleIndex < ohlc.length) {
                const candle = ohlc[candleIndex];
                return candle[1] >= candle[0] ? '#10b981' : '#ef4444'; // Green if close >= open
              }
              return '#6b7280';
            },
            opacity: 0.7
          }
        }
      ]
    };
  };

  const timeRanges = [
    { label: '1M', days: 30 },
    { label: '3M', days: 90 },
    { label: '6M', days: 180 },
    { label: '1Y', days: 365 },
    { label: 'MAX', days: 2000 }
  ];

  // Use the original data for price display (not filtered by time range)
  const allPrices = data?.ohlc || [];
  const latestPrice = allPrices[allPrices.length - 1]; // Latest price regardless of time range
  const prevPrice = allPrices[allPrices.length - 2];
  const change = latestPrice ? latestPrice[4] - (prevPrice?.[4] || latestPrice[4]) : 0; // p[4] is close
  const changePercent = latestPrice && prevPrice ? (change / prevPrice[4]) * 100 : 0; // prevPrice[4] is close

  return (
    <div className="p-6 space-y-6">
      {/* Header with Search */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{selectedTicker} Analysis</h1>
        <button
          onClick={handleRefresh}
          disabled={isFetching}
          className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Search Bar */}
      <div className="bg-white rounded-lg border p-4 shadow-sm">
        <h2 className="text-lg font-semibold mb-3">Search for Another Stock</h2>
        <TickerSearch 
          placeholder="Search for stocks (e.g., AAPL, MSFT, GOOGL)..." 
          onSelect={handleTickerSelect}
        />
      </div>

      {/* Price Info */}
      {latestPrice && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-lg border p-4 shadow-sm"
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="text-3xl font-bold">${latestPrice[4].toFixed(2)}</div>
              <div className={`flex items-center gap-1 text-sm ${
                change >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {change >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                ${Math.abs(change).toFixed(2)} ({Math.abs(changePercent).toFixed(2)}%)
              </div>
            </div>
            <div className="text-right text-sm text-gray-500">
              <div>Volume: {latestPrice[5].toLocaleString()}</div>
              <div>{new Date(latestPrice[0]).toLocaleDateString()}</div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Time Range Selector */}
      <div className="bg-white rounded-lg border p-4 shadow-sm">
        <h2 className="text-lg font-semibold mb-3">Time Range</h2>
        <div className="flex gap-2">
          {timeRanges.map((range) => (
            <button
              key={range.label}
              onClick={() => setTimeRange(range.days)}
              className={`px-4 py-2 rounded-lg transition-colors ${
                timeRange === range.days
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="bg-white rounded-lg border p-4 shadow-sm"
      >
        <h2 className="text-lg font-semibold mb-4">Price Chart</h2>
        {isLoading ? (
          <ChartSkeleton />
        ) : filteredPrices && filteredPrices.length > 0 ? (
          <ReactECharts
            option={getChartOption()}
            style={{ height: '500px', width: '100%' }}
            opts={{ renderer: 'canvas' }}
          />
        ) : (
          <div className="text-center py-12 text-gray-500">
            No chart data available
          </div>
        )}
      </motion.div>

      {/* Fundamentals */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="bg-white rounded-lg border p-4 shadow-sm"
      >
        <h2 className="text-lg font-semibold mb-4">Fundamentals</h2>
        <Fundamentals data={data?.fundamentals} />
      </motion.div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800 font-semibold">Error loading data</div>
          <div className="text-red-600 text-sm">{error.message}</div>
        </div>
      )}
    </div>
  );
}