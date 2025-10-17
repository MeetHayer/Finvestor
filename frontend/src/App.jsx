import { Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Home from './routes/Home';
import TickerDetail from './routes/TickerDetail';
import Watchlists from './routes/Watchlists';
import Portfolios from './routes/Portfolios';
import Compare from './routes/Compare';
import Methods from './routes/Methods';
import ErrorBoundary from './components/ErrorBoundary';

export default function App() {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/ticker" element={<TickerDetail />} />
            <Route path="/ticker/:symbol" element={<TickerDetail />} />
            <Route path="/watchlist" element={<Watchlists />} />
            <Route path="/portfolio" element={<Portfolios />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/methods" element={<Methods />} />
          </Routes>
        </ErrorBoundary>
      </main>
    </div>
  );
}
