import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, TrendingUp, Activity, Shield, BarChart3, AlertCircle } from 'lucide-react';

// Accordion Section Component
function AccordionSection({ title, icon: Icon, children, defaultOpen = false }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl border shadow-sm overflow-hidden mb-4"
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="w-10 h-10 rounded-lg bg-primary-50 flex items-center justify-center">
              <Icon className="w-5 h-5 text-primary-600" />
            </div>
          )}
          <h2 className="text-xl font-bold text-gray-900">{title}</h2>
        </div>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="w-5 h-5 text-gray-500" />
        </motion.div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-6 pb-6 space-y-4 text-gray-700 leading-relaxed">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function Methods() {
  return (
    <div className="container mx-auto px-6 py-8">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-4xl font-bold mb-3 text-gray-900">Methods & Methodologies</h1>
        <p className="text-gray-600 mb-8">
          Technical indicators, risk metrics, and data sources powering Finvestor's analysis.
        </p>
      </motion.div>

      {/* Data Sources */}
      <AccordionSection title="Data Sources" icon={BarChart3} defaultOpen={true}>
        <div>
          <h3 className="font-semibold text-lg mb-2">Historical Daily Data</h3>
          <p className="mb-3">
            Finvestor uses <strong>free public APIs</strong> including Yahoo Finance, Finnhub, and Alpha Vantage to fetch daily OHLCV (Open, High, Low, Close, Volume) data. 
            Historical price data is seeded from Kaggle datasets and stored locally for fast retrieval.
          </p>

          <h3 className="font-semibold text-lg mb-2 mt-4">Intraday 1-Minute Data</h3>
          <p className="mb-3">
            Real-time 1-minute candles are fetched using <strong>Yahoo Finance's free API</strong> via the yfinance Python library. 
            Due to API limitations, intraday data is typically limited to <strong>5-7 calendar days</strong> and may have gaps during non-trading hours.
          </p>

          <h3 className="font-semibold text-lg mb-2 mt-4">Risk-Free Rate</h3>
          <p>
            Sharpe ratio calculations use the <strong>FRED (Federal Reserve Economic Data)</strong> 3-month Treasury Bill rate as a proxy for the risk-free rate. 
            This data is fetched periodically and stored in the <code className="bg-gray-100 px-1 py-0.5 rounded text-sm">risk_free_series</code> table.
          </p>
        </div>

        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mt-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-yellow-800">Important Limitations</p>
              <ul className="text-sm text-yellow-700 mt-2 space-y-1 list-disc list-inside">
                <li>Free APIs may have rate limits, delays, or missing data</li>
                <li>Quotes are typically delayed 15-20 minutes during market hours</li>
                <li>Intraday data coverage varies by symbol and provider</li>
                <li>Data gaps may occur on weekends, holidays, and pre/post-market hours</li>
              </ul>
            </div>
          </div>
        </div>
      </AccordionSection>

      {/* Price Indicators */}
      <AccordionSection title="Price Indicators (SMA, EMA, RSI)" icon={TrendingUp}>
        <div>
          <h3 className="font-semibold text-lg mb-2">Simple Moving Average (SMA)</h3>
          <p className="mb-2">
            The <strong>Simple Moving Average</strong> is the arithmetic mean of closing prices over a fixed window of <em>n</em> periods.
            All prices in the window are weighted equally.
          </p>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 my-3 font-mono text-sm">
            SMA<sub>t</sub> = (1/n) × Σ<sub>i=0</sub><sup>n-1</sup> Price<sub>t-i</sub>
          </div>
          
          {/* SMA Period Comparison */}
          <div className="my-4 bg-white border-2 border-blue-200 rounded-lg p-4">
            <p className="font-semibold text-blue-900 mb-3">📊 SMA Period Comparison</p>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-3 p-2 bg-blue-50 rounded">
                <div className="w-24 font-bold text-blue-900">SMA-20</div>
                <div className="flex-1 h-2 bg-gradient-to-r from-blue-400 to-blue-300 rounded"></div>
                <div className="w-32 text-blue-800">Short-term (1 month)</div>
              </div>
              <div className="flex items-center gap-3 p-2 bg-indigo-50 rounded">
                <div className="w-24 font-bold text-indigo-900">SMA-50</div>
                <div className="flex-1 h-2 bg-gradient-to-r from-indigo-500 to-indigo-400 rounded"></div>
                <div className="w-32 text-indigo-800">Medium-term (2.5 months)</div>
              </div>
              <div className="flex items-center gap-3 p-2 bg-purple-50 rounded">
                <div className="w-24 font-bold text-purple-900">SMA-200</div>
                <div className="flex-1 h-2 bg-gradient-to-r from-purple-600 to-purple-500 rounded"></div>
                <div className="w-32 text-purple-800">Long-term (10 months)</div>
              </div>
            </div>
          </div>
          
          <div className="bg-blue-50 border-l-4 border-blue-400 p-3 my-3">
            <p className="font-medium text-blue-900">💡 Classic Trading Strategies:</p>
            <ul className="text-sm text-blue-800 mt-2 space-y-2 list-disc list-inside">
              <li>
                <strong>Golden Cross:</strong> When SMA-50 crosses above SMA-200 → Strong bullish signal 
                (historically reliable for long-term trend changes)
              </li>
              <li>
                <strong>Death Cross:</strong> When SMA-50 crosses below SMA-200 → Strong bearish signal 
                (warning to exit positions or hedge)
              </li>
              <li>
                <strong>Price vs SMA-200:</strong> Trading above 200-day SMA = bull market territory. 
                Below = bear market. This is watched by institutional investors worldwide.
              </li>
              <li>
                <strong>Support/Resistance:</strong> Moving averages often act as dynamic support (in uptrends) 
                or resistance (in downtrends)
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-6">
          <h3 className="font-semibold text-lg mb-2">Exponential Moving Average (EMA)</h3>
          <p className="mb-2">
            The <strong>Exponential Moving Average</strong> applies more weight to recent prices, making it more responsive to new information than SMA.
            Recent prices have <em>exponentially</em> more influence than older prices.
          </p>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 my-3 font-mono text-sm">
            EMA<sub>t</sub> = EMA<sub>t-1</sub> + α × (Price<sub>t</sub> - EMA<sub>t-1</sub>)
            <br />
            where α = 2 / (n + 1)
          </div>
          
          {/* EMA vs SMA Comparison */}
          <div className="my-4 bg-white border-2 border-green-200 rounded-lg p-4">
            <p className="font-semibold text-green-900 mb-3">⚡ EMA vs SMA: Key Differences</p>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-blue-50 border border-blue-200 rounded p-3">
                <p className="font-bold text-blue-900 mb-1">SMA (Simple)</p>
                <ul className="text-blue-800 space-y-1">
                  <li>• Equal weight to all prices</li>
                  <li>• Smoother line</li>
                  <li>• Slower to react</li>
                  <li>• Better for long-term trends</li>
                </ul>
              </div>
              <div className="bg-green-50 border border-green-200 rounded p-3">
                <p className="font-bold text-green-900 mb-1">EMA (Exponential)</p>
                <ul className="text-green-800 space-y-1">
                  <li>• More weight to recent prices</li>
                  <li>• Choppier, reactive line</li>
                  <li>• Faster to react</li>
                  <li>• Better for short-term momentum</li>
                </ul>
              </div>
            </div>
          </div>
          
          <div className="bg-green-50 border-l-4 border-green-400 p-3 my-3">
            <p className="font-medium text-green-900">💡 MACD Strategy (Uses EMAs):</p>
            <div className="text-sm text-green-800 mt-2 space-y-2">
              <p className="font-semibold">MACD = EMA(12) - EMA(26)</p>
              <ul className="list-disc list-inside space-y-1">
                <li><strong>MACD crosses above signal line:</strong> Bullish momentum building → Buy signal</li>
                <li><strong>MACD crosses below signal line:</strong> Bearish momentum building → Sell signal</li>
                <li><strong>MACD histogram expanding:</strong> Trend strengthening</li>
                <li><strong>MACD histogram contracting:</strong> Trend weakening, potential reversal</li>
              </ul>
              <div className="mt-2 bg-green-100 p-2 rounded">
                <p className="font-semibold">Why Traders Love MACD:</p>
                <p>It combines trend following (EMA crossovers) AND momentum (histogram) in one indicator. 
                Professional traders use it to time entries/exits with precision.</p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6">
          <h3 className="font-semibold text-lg mb-2">Relative Strength Index (RSI)</h3>
          <p className="mb-2">
            The <strong>RSI</strong> is a momentum oscillator that measures the speed and magnitude of price changes on a scale from 0 to 100.
          </p>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 my-3 font-mono text-sm">
            RS = (Avg Gain over n periods) / (Avg Loss over n periods)
            <br />
            RSI = 100 - [100 / (1 + RS)]
          </div>
          <p className="mb-2">
            Typical period is <strong>14 days</strong>. RSI values are bounded between 0 and 100.
          </p>
          
          {/* Interactive RSI Visualization */}
          <div className="my-4 bg-white border-2 border-purple-200 rounded-lg p-4">
            <p className="font-semibold text-purple-900 mb-3">📊 RSI Zones (Interactive Visual)</p>
            
            {/* RSI Scale */}
            <div className="relative h-16 mb-3">
              {/* Background gradient */}
              <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-green-400 via-yellow-300 to-red-400"></div>
              
              {/* Zone labels */}
              <div className="absolute inset-0 flex items-center justify-between px-2 text-xs font-bold">
                <span className="text-green-900 bg-white/80 px-2 py-1 rounded">0 (Oversold)</span>
                <span className="text-gray-700 bg-white/80 px-2 py-1 rounded">50 (Neutral)</span>
                <span className="text-red-900 bg-white/80 px-2 py-1 rounded">100 (Overbought)</span>
              </div>
              
              {/* Threshold lines */}
              <div className="absolute left-[30%] top-0 bottom-0 w-0.5 bg-green-700 opacity-50"></div>
              <div className="absolute left-[70%] top-0 bottom-0 w-0.5 bg-red-700 opacity-50"></div>
            </div>
            
            {/* Zone descriptions */}
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="bg-green-50 border border-green-200 rounded p-2">
                <p className="font-bold text-green-900">RSI &lt; 30</p>
                <p className="text-green-800">Oversold - Potential reversal up</p>
              </div>
              <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
                <p className="font-bold text-gray-900">30 &lt; RSI &lt; 70</p>
                <p className="text-gray-700">Neutral - Normal range</p>
              </div>
              <div className="bg-red-50 border border-red-200 rounded p-2">
                <p className="font-bold text-red-900">RSI &gt; 70</p>
                <p className="text-red-800">Overbought - Potential pullback</p>
              </div>
            </div>
          </div>
          
          <div className="bg-purple-50 border-l-4 border-purple-400 p-3 my-3">
            <p className="font-medium text-purple-900">💡 Advanced Trading Strategies:</p>
            <ul className="text-sm text-purple-800 mt-2 space-y-2 list-disc list-inside">
              <li>
                <strong>Oversold Bounce:</strong> When RSI drops below 30, wait for it to cross back above 30 before buying 
                (confirms momentum shift)
              </li>
              <li>
                <strong>Overbought Fade:</strong> When RSI exceeds 70, consider taking profits or tightening stop-losses 
                (but note: strong trends can stay overbought for weeks!)
              </li>
              <li>
                <strong>Divergence Trading:</strong> If price makes new highs but RSI doesn't → bearish divergence (potential reversal).
                If price makes new lows but RSI doesn't → bullish divergence (potential bounce)
              </li>
              <li>
                <strong>50-Line Crossovers:</strong> RSI crossing above 50 = bullish momentum. Crossing below 50 = bearish momentum
              </li>
            </ul>
          </div>
          
          {/* Real-World Example */}
          <div className="bg-indigo-50 border-2 border-indigo-200 rounded-lg p-4 my-3">
            <p className="font-bold text-indigo-900 mb-2">📈 Example: AAPL Stock Scenario</p>
            <div className="space-y-2 text-sm text-indigo-800">
              <p><strong>Day 1:</strong> AAPL = $180, RSI = 75 (Overbought) → ⚠️ Caution, potential pullback</p>
              <p><strong>Day 7:</strong> AAPL = $172, RSI = 28 (Oversold) → 💡 Potential buy opportunity</p>
              <p><strong>Day 10:</strong> AAPL = $175, RSI = 45 (Recovery) → ✅ Bounce confirmed, trend improving</p>
              <p className="pt-2 border-t border-indigo-300">
                <strong>Lesson:</strong> RSI helped identify both the peak (75) and the bottom (28), giving clear entry/exit signals.
                However, always combine with other analysis - no indicator is perfect!
              </p>
            </div>
          </div>
        </div>
      </AccordionSection>

      {/* Risk and Portfolio Metrics */}
      <AccordionSection title="Risk & Portfolio Metrics" icon={Shield}>
        <div>
          <h3 className="font-semibold text-lg mb-2">Volatility (Annualized)</h3>
          <p className="mb-2">
            <strong>Volatility</strong> measures the dispersion of returns, typically expressed as the annualized standard deviation of daily returns.
          </p>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 my-3 font-mono text-sm">
            σ<sub>annual</sub> = σ<sub>daily</sub> × √252
          </div>
          <p>
            Where <em>σ<sub>daily</sub></em> is the standard deviation of daily returns, and <strong>252</strong> is the typical number of trading days per year. 
            Higher volatility means wider price swings (both gains and losses).
          </p>
        </div>

        <div className="mt-6">
          <h3 className="font-semibold text-lg mb-2">Sharpe Ratio</h3>
          <p className="mb-2">
            The <strong>Sharpe Ratio</strong> measures risk-adjusted return: how much excess return you earn per unit of risk.
          </p>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 my-3 font-mono text-sm">
            Sharpe = (R<sub>p</sub> - R<sub>f</sub>) / σ<sub>p</sub>
          </div>
          <p className="mb-2">
            Where:
          </p>
          <ul className="text-sm list-disc list-inside space-y-1 ml-4">
            <li><em>R<sub>p</sub></em> = Portfolio return (annualized)</li>
            <li><em>R<sub>f</sub></em> = Risk-free rate (e.g., 3-month T-Bill)</li>
            <li><em>σ<sub>p</sub></em> = Portfolio volatility (annualized)</li>
          </ul>
          <p className="mt-2">
            <strong>Interpretation:</strong> A higher Sharpe ratio indicates better risk-adjusted performance. 
            A Sharpe &gt; 1 is generally considered good; &gt; 2 is very good.
          </p>
          <div className="bg-orange-50 border-l-4 border-orange-400 p-3 my-3">
            <p className="text-sm text-orange-800">
              <strong>Note:</strong> Sharpe ratio assumes returns are normally distributed and is sensitive to the time window chosen. 
              It's best used for comparing similar portfolios over similar periods.
            </p>
          </div>
        </div>

        <div className="mt-6">
          <h3 className="font-semibold text-lg mb-2">Max Drawdown</h3>
          <p className="mb-2">
            <strong>Max Drawdown</strong> is the largest peak-to-trough decline in portfolio value during a given period, expressed as a percentage.
          </p>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 my-3 font-mono text-sm">
            Max DD = (Trough Value - Peak Value) / Peak Value
          </div>
          <p>
            This metric highlights the worst-case loss you would have experienced if you bought at the peak and sold at the trough. 
            It's a key measure of <strong>downside risk</strong> and helps investors understand how painful a losing streak could be.
          </p>
        </div>

        <div className="mt-6">
          <h3 className="font-semibold text-lg mb-2">Value-at-Risk (VaR) — 1-Day, 95% Confidence</h3>
          <p className="mb-2">
            <strong>Value-at-Risk</strong> estimates the maximum loss you could expect over a given time horizon (1 day) with a given confidence level (95%).
          </p>
          <p className="mb-2">
            Finvestor uses the <strong>historical method</strong>: we look at the distribution of past daily returns and find the 5th percentile (the threshold below which 5% of worst days fall).
          </p>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 my-3 text-sm">
            <strong>Example:</strong> If your portfolio is worth $10,000 and the 1-day 95% VaR is $320, 
            this means that on a typical day, you should not lose more than $320 with 95% confidence. 
            However, 5% of the time (roughly 1 in 20 days), losses could exceed this amount.
          </div>
          <div className="bg-red-50 border-l-4 border-red-400 p-3 my-3">
            <p className="text-sm text-red-800">
              <strong>Important:</strong> VaR is an <em>educational approximation</em>, not regulatory-grade risk measurement. 
              It assumes the future will resemble the past and does not capture "black swan" events. 
              Requires at least 50 daily observations for reasonable accuracy.
            </p>
          </div>
        </div>

        <div className="mt-6">
          <h3 className="font-semibold text-lg mb-2">Asset Allocation & Diversification</h3>
          <p className="mb-2">
            <strong>Asset allocation</strong> is how you divide your portfolio across different asset classes (stocks, bonds, cash) or sectors (tech, healthcare, energy).
          </p>
          <p className="mb-2">
            <strong>Diversification</strong> reduces unsystematic risk by holding multiple uncorrelated assets. A well-diversified portfolio can lower volatility and max drawdown without necessarily sacrificing long-term returns.
          </p>
          <div className="bg-indigo-50 border-l-4 border-indigo-400 p-3 my-3">
            <p className="text-sm text-indigo-800">
              <strong>Strategy Tip:</strong> Finvestor currently focuses on equities, but the same risk metrics apply to multi-asset portfolios. 
              Consider mixing asset classes and sectors to smooth out returns and reduce peak-to-trough drawdowns.
            </p>
          </div>
        </div>
      </AccordionSection>

      {/* Assumptions and Limitations */}
      <AccordionSection title="Assumptions & Limitations" icon={AlertCircle}>
        <div className="space-y-4">
          <div>
            <h3 className="font-semibold text-lg mb-2">Price Data & Timing</h3>
            <ul className="list-disc list-inside space-y-1 text-sm">
              <li>All metrics use <strong>daily closing prices</strong> for historical data</li>
              <li>Intraday charts use 1-minute candles but may have gaps during non-trading hours</li>
              <li>Free API quotes are typically <strong>delayed 15-20 minutes</strong></li>
              <li>Weekend and holiday data may be missing or interpolated</li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold text-lg mb-2">Statistical Assumptions</h3>
            <ul className="list-disc list-inside space-y-1 text-sm">
              <li>Volatility and Sharpe calculations assume <strong>log-normal returns</strong> (returns follow a normal distribution)</li>
              <li>In reality, financial returns have "fat tails" — extreme events are more common than normal distributions predict</li>
              <li>VaR is backward-looking and assumes past return distributions are representative of future risk</li>
              <li>Risk metrics require sufficient data: <strong>≥30 observations for volatility</strong>, <strong>≥50 for VaR</strong></li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold text-lg mb-2">Trading Costs & Slippage</h3>
            <ul className="list-disc list-inside space-y-1 text-sm">
              <li>Finvestor's portfolio simulations do <strong>not account for transaction costs</strong>, commissions, or slippage</li>
              <li>In practice, frequent trading incurs costs that can erode returns</li>
              <li>Backtest performance is <strong>not predictive</strong> of future results</li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold text-lg mb-2">Data Quality & Gaps</h3>
            <ul className="list-disc list-inside space-y-1 text-sm">
              <li>Free data sources may have <strong>missing data, corporate actions (splits/dividends) not fully adjusted</strong></li>
              <li>Intraday data availability varies by symbol and may be incomplete for less liquid stocks</li>
              <li>Always cross-reference critical decisions with a paid, reliable data provider</li>
            </ul>
          </div>

          <div className="bg-gray-100 border border-gray-300 rounded-lg p-4 mt-6">
            <h3 className="font-bold text-lg mb-2 text-gray-900">Educational Use Only</h3>
            <p className="text-sm text-gray-800">
              <strong>Finvestor is an educational tool.</strong> It is not investment advice, and simulated performance is not a guarantee of future results. 
              The metrics, indicators, and strategies described here are for <strong>learning purposes only</strong>. 
              Always consult a licensed financial advisor before making investment decisions.
            </p>
          </div>
        </div>
      </AccordionSection>

      {/* Links to Other Pages */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="bg-gradient-to-r from-primary-50 to-blue-50 border border-primary-200 rounded-xl p-6 mt-8"
      >
        <h3 className="font-bold text-lg mb-3 text-gray-900">Explore Finvestor</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <div>
            <Activity className="w-4 h-4 inline mr-2 text-primary-600" />
            <strong>Ticker Page:</strong> Toggle SMA, EMA, RSI overlays on historical and intraday charts
          </div>
          <div>
            <Shield className="w-4 h-4 inline mr-2 text-primary-600" />
            <strong>Portfolio Page:</strong> View risk metrics (Sharpe, VaR, Max Drawdown) with detailed explanations
          </div>
          <div>
            <BarChart3 className="w-4 h-4 inline mr-2 text-primary-600" />
            <strong>Watchlist Page:</strong> Track daily/weekly changes, market cap, P/E ratio, and beta
          </div>
          <div>
            <TrendingUp className="w-4 h-4 inline mr-2 text-primary-600" />
            <strong>Portfolio Chart:</strong> Compare your returns against major benchmarks (SPY, QQQ, DIA)
          </div>
        </div>
      </motion.div>
    </div>
  );
}
