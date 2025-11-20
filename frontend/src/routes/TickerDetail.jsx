import { useState, useMemo, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import { motion } from 'framer-motion';
import { Star, RefreshCw, TrendingUp, TrendingDown, Clock } from 'lucide-react';
import toast from 'react-hot-toast';
import { useSafeQuery as useQuery } from '../lib/querySafe';
import { getJSON } from '../lib/http';
import Fundamentals from '../components/Fundamentals';
import { ChartSkeleton } from '../components/LoadingSkeleton';
import TickerSearch from '../components/TickerSearch';
import { SMA, EMA, RSI } from '../lib/indicators';
import { useIntradayData } from '../hooks/useIntradayData';

export default function TickerDetail() {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const [timeRange, setTimeRange] = useState(365);
  const [selectedTicker, setSelectedTicker] = useState(symbol || null);
  const [chartType, setChartType] = useState('candles'); // 'candles' | 'line'
  const [showSMA, setShowSMA] = useState(false);
  const [showEMA, setShowEMA] = useState(false);
  const [showRSI, setShowRSI] = useState(false);
  const [smaPeriod, setSmaPeriod] = useState(20);
  const [emaPeriod, setEmaPeriod] = useState(20);
  const [rsiPeriod, setRsiPeriod] = useState(14);
  const [activeTab, setActiveTab] = useState('historical'); // 'historical' | 'intraday'
  const [lastIntradayUpdate, setLastIntradayUpdate] = useState(null);

  // Use React Query for data fetching with caching
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['marketData', selectedTicker, timeRange],
    queryFn: () => getJSON(`/data/${selectedTicker}?range_days=${timeRange}`),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    enabled: Boolean(selectedTicker && selectedTicker.trim().length > 0),
    retry: 2,
  });

  // Intraday data hook
  const { 
    data: intradayData, 
    isLoading: intradayLoading, 
    error: intradayError,
    refetch: refetchIntraday 
  } = useIntradayData(selectedTicker, 7);

  // Auto-refresh intraday data every 60 seconds when on intraday tab
  useEffect(() => {
    if (activeTab !== 'intraday') return;
    
    const intervalId = setInterval(() => {
      refetchIntraday().then(() => {
        setLastIntradayUpdate(new Date());
      });
    }, 60000); // 60 seconds
    
    // Set initial update time
    if (intradayData && !lastIntradayUpdate) {
      setLastIntradayUpdate(new Date());
    }
    
    return () => clearInterval(intervalId);
  }, [activeTab, refetchIntraday, intradayData, lastIntradayUpdate]);

  // Update URL when ticker changes
  useEffect(() => {
    if (selectedTicker && selectedTicker !== symbol) {
      navigate(`/ticker/${selectedTicker}`, { replace: true });
    }
  }, [selectedTicker, symbol, navigate]);

  const handleRefresh = async () => {
    // Call with refresh=1 to fetch fresh data from yahooquery
    const promise = getJSON(`/data/${selectedTicker}?range_days=${timeRange}&refresh=1`)
      .then(() => refetch());
    toast.promise(promise, {
      loading: 'Refreshing data from live sources...',
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

  const closes = useMemo(() => (filteredPrices || []).map(p => Number(p?.[4] ?? 0)), [filteredPrices]);
  const sma = useMemo(() => showSMA ? SMA(closes, smaPeriod) : null, [showSMA, closes, smaPeriod]);
  const ema = useMemo(() => showEMA ? EMA(closes, emaPeriod) : null, [showEMA, closes, emaPeriod]);
  const rsi = useMemo(() => showRSI ? RSI(closes, rsiPeriod) : null, [showRSI, closes, rsiPeriod]);

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
    
    // Backend format: [timestamp, open, high, low, close, volume]
    // ECharts candlestick format: [open, close, lowest, highest]
    const ohlc = prices.map(p => [p[1], p[4], p[3], p[2]]); // [open, close, low, high]
    const volumes = prices.map(p => p[5]);
    
    // Debug: Log a sample to verify format
    if (prices.length > 0) {
      console.log('Sample backend data:', prices[prices.length - 1]);
      console.log('Mapped to candlestick:', ohlc[ohlc.length - 1]);
    }

    const option = {
      animation: true,
      backgroundColor: '#ffffff',
      // Add dataZoom for interactive zooming
      dataZoom: [
        {
          type: 'inside', // Mouse wheel zoom
          xAxisIndex: [0, 1],
          start: 0,
          end: 100,
          zoomOnMouseWheel: true,
          moveOnMouseMove: true,
          moveOnMouseWheel: false
        },
        {
          type: 'slider', // Slider bar at bottom
          xAxisIndex: [0, 1],
          start: 0,
          end: 100,
          top: '90%',
          height: 20,
          handleSize: '80%',
          handleStyle: {
            color: '#3b82f6',
            borderColor: '#1d4ed8'
          },
          textStyle: {
            color: '#666'
          },
          borderColor: '#ddd',
          fillerColor: 'rgba(59, 130, 246, 0.2)',
          dataBackground: {
            lineStyle: {
              color: '#3b82f6'
            },
            areaStyle: {
              color: 'rgba(59, 130, 246, 0.1)'
            }
          }
        }
      ],
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
        backgroundColor: 'rgba(0, 0, 0, 0.9)',
        borderColor: '#333',
        borderWidth: 1,
        textStyle: {
          color: '#fff'
        },
        formatter: function (params) {
          const dateIndex = params[0].dataIndex;
          const backendData = prices[dateIndex]; // Get original backend data
          
          let result = `<div style="font-weight: bold; margin-bottom: 8px; color: #fff; border-bottom: 1px solid #555; padding-bottom: 4px;">${params[0].axisValue}</div>`;
          
          let volumeValue = null;
          let rsiValue = null;
          let smaValue = null;
          let emaValue = null;
          
          params.forEach(param => {
            if (param.seriesName === selectedTicker) {
              // Get values directly from backend data for accuracy
              // Backend format: [timestamp, open, high, low, close, volume]
              const open = backendData[1];
              const high = backendData[2];
              const low = backendData[3];
              const close = backendData[4];
              const isGreen = close >= open;
              
              result += `
                <div style="margin: 8px 0; line-height: 1.6;">
                  <div style="margin: 2px 0;"><span style="color: #aaa;">Open:</span> <span style="color: #fff; font-weight: bold;">$${open.toFixed(2)}</span></div>
                  <div style="margin: 2px 0;"><span style="color: #aaa;">High:</span> <span style="color: #10b981; font-weight: bold;">$${high.toFixed(2)}</span></div>
                  <div style="margin: 2px 0;"><span style="color: #aaa;">Low:</span> <span style="color: #ef4444; font-weight: bold;">$${low.toFixed(2)}</span></div>
                  <div style="margin: 2px 0;"><span style="color: #aaa;">Close:</span> <span style="color: ${isGreen ? '#10b981' : '#ef4444'}; font-weight: bold;">$${close.toFixed(2)}</span></div>
                  <div style="margin: 4px 0; padding-top: 4px; border-top: 1px solid #555;"><span style="color: #aaa;">Change:</span> <span style="color: ${isGreen ? '#10b981' : '#ef4444'}; font-weight: bold;">${isGreen ? '+' : ''}$${(close - open).toFixed(2)} (${isGreen ? '+' : ''}${((close - open) / open * 100).toFixed(2)}%)</span></div>
                </div>
              `;
            } else if (param.seriesName === 'Volume') {
              volumeValue = param.data;
            } else if (param.seriesName && param.seriesName.startsWith('RSI')) {
              rsiValue = param.data;
            } else if (param.seriesName && param.seriesName.startsWith('SMA')) {
              smaValue = param.data;
            } else if (param.seriesName && param.seriesName.startsWith('EMA')) {
              emaValue = param.data;
            }
          });
          
          // Add SMA/EMA indicators if present
          if (smaValue !== null || emaValue !== null) {
            result += `<div style="margin: 4px 0; padding-top: 4px; border-top: 1px solid #555;">`;
            if (smaValue !== null && smaValue !== undefined && !isNaN(smaValue)) {
              result += `<div style="margin: 2px 0;"><span style="color: #aaa;">SMA(${smaPeriod}):</span> <span style="color: #3b82f6; font-weight: bold;">$${smaValue.toFixed(2)}</span></div>`;
            }
            if (emaValue !== null && emaValue !== undefined && !isNaN(emaValue)) {
              result += `<div style="margin: 2px 0;"><span style="color: #aaa;">EMA(${emaPeriod}):</span> <span style="color: #8b5cf6; font-weight: bold;">$${emaValue.toFixed(2)}</span></div>`;
            }
            result += `</div>`;
          }
          
          // Add volume and RSI in a combined section at the bottom
          if (volumeValue !== null || rsiValue !== null) {
            result += `<div style="margin: 4px 0; padding-top: 4px; border-top: 1px solid #555;">`;
            if (volumeValue !== null) {
              result += `<div style="margin: 2px 0;"><span style="color: #aaa;">Volume:</span> <span style="color: #fff; font-weight: bold;">${volumeValue.toLocaleString()}</span></div>`;
            }
            if (rsiValue !== null) {
              const rsiColor = rsiValue > 70 ? '#ef4444' : rsiValue < 30 ? '#10b981' : '#fff';
              result += `<div style="margin: 2px 0;"><span style="color: #aaa;">RSI:</span> <span style="color: ${rsiColor}; font-weight: bold;">${rsiValue.toFixed(2)}</span></div>`;
            }
            result += `</div>`;
          }
          
          return result;
        }
      },
      legend: { show: true },
      grid: [
        { left: 40, right: 20, top: 20, height: '62%' },
        { left: 40, right: 20, top: '70%', height: '24%' }
      ],
      xAxis: [
        { type: 'category', data: dates, boundaryGap: false, axisLabel: { hideOverlap: true } },
        { type: 'category', data: dates, boundaryGap: false, gridIndex: 1, axisLabel: { hideOverlap: true } }
      ],
      yAxis: [
        { scale: true },
        { scale: true, gridIndex: 1, name: 'Volume', nameGap: 28 },
        { min: 0, max: 100, gridIndex: 1, position: 'right', name: 'RSI', nameGap: 28, splitNumber: 5 }
      ],
      series: []
    };

    const priceSeries = chartType === 'candles'
      ? [{ name: selectedTicker, type: 'candlestick', data: ohlc, xAxisIndex: 0, yAxisIndex: 0, itemStyle: { color: '#10b981', color0: '#ef4444', borderColor: '#10b981', borderColor0: '#ef4444', borderWidth: 1 } }]
      : [{ name: selectedTicker, type: 'line', data: closes, xAxisIndex: 0, yAxisIndex: 0, smooth: true, showSymbol: false, lineStyle: { width: 2 } }];

    const overlaySeries = [];
    if (showSMA && sma) overlaySeries.push({ name: `SMA(${smaPeriod})`, type: 'line', data: sma, xAxisIndex: 0, yAxisIndex: 0, smooth: true, showSymbol: false, lineStyle: { width: 1 } });
    if (showEMA && ema) overlaySeries.push({ name: `EMA(${emaPeriod})`, type: 'line', data: ema, xAxisIndex: 0, yAxisIndex: 0, smooth: true, showSymbol: false, lineStyle: { width: 1 } });

    option.series.push(...priceSeries, ...overlaySeries);
    option.series.push({
      name: 'Volume',
      type: 'bar',
      xAxisIndex: 1,
      yAxisIndex: 1,
      data: volumes,
      itemStyle: {
        color: function(params) {
          const candleIndex = params.dataIndex;
          if (candleIndex < ohlc.length) {
            const candle = ohlc[candleIndex];
            return candle[1] >= candle[0] ? '#10b981' : '#ef4444';
          }
          return '#6b7280';
        },
        opacity: 0.7
      }
    });

    if (showRSI && rsi) {
      option.series.push({
        name: `RSI(${rsiPeriod})`,
        type: 'line',
        xAxisIndex: 1,
        yAxisIndex: 2,
        data: rsi,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1 }
      });
    }

    return option;
  };

  const getIntradayChartOption = (intradayData) => {
    if (!intradayData?.candles || intradayData.candles.length === 0) return {};

    // intradayData.candles format: ["2025-11-19T14:30:00Z", open, high, low, close, volume]
    const candles = intradayData.candles;
    const times = candles.map(c => {
      const date = new Date(c[0]);
      return date.toLocaleString('en-US', { 
        month: 'numeric', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    });
    
    // ECharts candlestick format: [open, close, low, high]
    const ohlc = candles.map(c => [c[1], c[4], c[3], c[2]]);
    const volumes = candles.map(c => c[5]);

    return {
      animation: true,
      backgroundColor: '#ffffff',
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1],
          start: 85, // Show recent data by default
          end: 100
        },
        {
          type: 'slider',
          xAxisIndex: [0, 1],
          start: 85,
          end: 100,
          top: '90%',
          height: 20
        }
      ],
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: 'rgba(0, 0, 0, 0.9)',
        textStyle: { color: '#fff' },
        formatter: function (params) {
          const dataIndex = params[0].dataIndex;
          const candle = candles[dataIndex];
          const [timestamp, open, high, low, close, volume] = candle;
          const isGreen = close >= open;
          
          return `
            <div style="font-weight: bold; margin-bottom: 8px; border-bottom: 1px solid #555; padding-bottom: 4px;">
              ${new Date(timestamp).toLocaleString()}
            </div>
            <div style="margin: 8px 0; line-height: 1.6;">
              <div style="margin: 2px 0;"><span style="color: #aaa;">Open:</span> <span style="color: #fff; font-weight: bold;">$${open.toFixed(2)}</span></div>
              <div style="margin: 2px 0;"><span style="color: #aaa;">High:</span> <span style="color: #10b981; font-weight: bold;">$${high.toFixed(2)}</span></div>
              <div style="margin: 2px 0;"><span style="color: #aaa;">Low:</span> <span style="color: #ef4444; font-weight: bold;">$${low.toFixed(2)}</span></div>
              <div style="margin: 2px 0;"><span style="color: #aaa;">Close:</span> <span style="color: ${isGreen ? '#10b981' : '#ef4444'}; font-weight: bold;">$${close.toFixed(2)}</span></div>
              <div style="margin: 4px 0; padding-top: 4px; border-top: 1px solid #555;">
                <span style="color: #aaa;">Volume:</span> <span style="color: #fff; font-weight: bold;">${volume.toLocaleString()}</span>
              </div>
            </div>
          `;
        }
      },
      grid: [
        { left: '10%', right: '10%', top: '5%', height: '60%' },
        { left: '10%', right: '10%', top: '71%', height: '15%' }
      ],
      xAxis: [
        {
          type: 'category',
          data: times,
          boundaryGap: true,
          axisLine: { lineStyle: { color: '#ccc' } },
          splitLine: { show: false },
          axisLabel: { rotate: 45, fontSize: 10 }
        },
        {
          type: 'category',
          gridIndex: 1,
          data: times,
          boundaryGap: true,
          axisLine: { lineStyle: { color: '#ccc' } },
          axisLabel: { show: false }
        }
      ],
      yAxis: [
        {
          type: 'value',
          scale: true,
          splitLine: { lineStyle: { color: '#f0f0f0' } },
          axisLabel: {
            formatter: (value) => `$${value.toFixed(2)}`
          }
        },
        {
          type: 'value',
          gridIndex: 1,
          scale: true,
          splitLine: { show: false },
          axisLabel: { show: false }
        }
      ],
      series: [
        {
          name: selectedTicker,
          type: 'candlestick',
          data: ohlc,
          itemStyle: {
            color: '#10b981',
            color0: '#ef4444',
            borderColor: '#059669',
            borderColor0: '#dc2626'
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
              const candle = candles[params.dataIndex];
              return candle[4] >= candle[1] ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)';
            }
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

  // Extract company name from fundamentals
  const companyName = data?.fundamentals?.longName || data?.fundamentals?.shortName || '';

  return (
    <div className="p-6 space-y-6">
      {/* Header with Search */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{selectedTicker}</h1>
          {companyName && (
            <p className="text-sm text-gray-600 mt-1">{companyName}</p>
          )}
        </div>
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

      {/* Chart Controls */}
      <div className="bg-white rounded-lg border p-4 shadow-sm">
        <div className="flex gap-2 items-center my-2">
          <button className={`px-3 py-1 rounded ${chartType==='candles' ? 'bg-black text-white' : 'bg-gray-100'}`} onClick={() => setChartType('candles')}>Candles</button>
          <button className={`px-3 py-1 rounded ${chartType==='line' ? 'bg-black text-white' : 'bg-gray-100'}`} onClick={() => setChartType('line')}>Line</button>
          <label className="ml-4 flex items-center gap-1 text-sm"><input type="checkbox" checked={showSMA} onChange={e => setShowSMA(e.target.checked)}/>SMA</label>
          <input className="w-16 border rounded px-1 text-sm" type="number" min="2" value={smaPeriod} onChange={e => setSmaPeriod(Number(e.target.value||20))}/>
          <label className="ml-2 flex items-center gap-1 text-sm"><input type="checkbox" checked={showEMA} onChange={e => setShowEMA(e.target.checked)}/>EMA</label>
          <input className="w-16 border rounded px-1 text-sm" type="number" min="2" value={emaPeriod} onChange={e => setEmaPeriod(Number(e.target.value||20))}/>
          <label className="ml-2 flex items-center gap-1 text-sm"><input type="checkbox" checked={showRSI} onChange={e => setShowRSI(e.target.checked)}/>RSI</label>
          <input className="w-16 border rounded px-1 text-sm" type="number" min="2" value={rsiPeriod} onChange={e => setRsiPeriod(Number(e.target.value||14))}/>
        </div>
      </div>

      {/* Chart with Tabs */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="bg-white rounded-lg border shadow-sm"
      >
        {/* Tab Header */}
        <div className="border-b px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('historical')}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${
                activeTab === 'historical'
                  ? 'bg-primary-600 text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Historical
            </button>
            <button
              onClick={() => {
                setActiveTab('intraday');
                if (!lastIntradayUpdate) {
                  setLastIntradayUpdate(new Date());
                }
              }}
              className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
                activeTab === 'intraday'
                  ? 'bg-primary-600 text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Clock className="w-4 h-4" />
              Intraday (1m)
            </button>
          </div>
          
          {activeTab === 'intraday' && lastIntradayUpdate && (
            <div className="text-xs text-gray-500">
              Updated at {lastIntradayUpdate.toLocaleTimeString()}
            </div>
          )}
        </div>

        {/* Chart Content */}
        <div className="p-4">
          {activeTab === 'historical' ? (
            // Historical Chart
            <>
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
            </>
          ) : (
            // Intraday Chart
            <>
              <h2 className="text-lg font-semibold mb-2">Intraday Chart (1-minute bars)</h2>
              <p className="text-sm text-gray-500 mb-4">
                Last 7 days of 1-minute candles. Auto-refreshes every 60 seconds.
              </p>
              {intradayLoading ? (
                <ChartSkeleton />
              ) : intradayError ? (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
                  <p className="text-yellow-800 font-medium mb-1">Intraday data unavailable</p>
                  <p className="text-sm text-yellow-700">
                    {intradayError.message || 'Provider may be unavailable or symbol invalid'}
                  </p>
                </div>
              ) : intradayData?.candles && intradayData.candles.length > 0 ? (
                <>
                  <ReactECharts
                    option={getIntradayChartOption(intradayData)}
                    style={{ height: '500px', width: '100%' }}
                    opts={{ renderer: 'canvas' }}
                  />
                  {intradayData.note && (
                    <p className="text-xs text-gray-500 mt-2 italic">
                      Note: {intradayData.note}
                    </p>
                  )}
                </>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  No intraday data available
                </div>
              )}
            </>
          )}
        </div>
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