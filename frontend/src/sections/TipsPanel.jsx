import { useState, useEffect } from 'react';
import { PRO_TIPS } from '../data/proTips';

export default function TipsPanel() {
  const [currentTip, setCurrentTip] = useState(0);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    if (showAll) return; // Don't rotate when viewing all
    
    const interval = setInterval(() => {
      setCurrentTip((prev) => (prev + 1) % PRO_TIPS.length);
    }, 5000); // Rotate every 5 seconds

    return () => clearInterval(interval);
  }, [showAll]);

  if (showAll) {
    return (
      <div className="rounded-2xl border bg-white p-6 shadow-sm max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">All Pro Tips ({PRO_TIPS.length})</h2>
          <button
            onClick={() => setShowAll(false)}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            ← Back to Rotation
          </button>
        </div>
        <div className="space-y-3">
          {PRO_TIPS.map((tip, index) => (
            <div key={index} className="flex gap-3 text-sm text-gray-700 pb-3 border-b border-gray-100 last:border-0">
              <span className="text-blue-600 font-semibold min-w-[2rem]">{index + 1}.</span>
              <span>{tip}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Pro Tips</h2>
        <button
          onClick={() => setShowAll(true)}
          className="text-xs text-blue-600 hover:text-blue-700 font-medium"
        >
          View All {PRO_TIPS.length}
        </button>
      </div>
      <div className="relative h-20 overflow-hidden">
        <div 
          className="absolute inset-0 transition-transform duration-500 ease-in-out"
          style={{ transform: `translateY(-${currentTip * 100}%)` }}
        >
          {PRO_TIPS.map((tip, index) => (
            <div key={index} className="h-20 flex items-center text-sm text-gray-700">
              {tip}
            </div>
          ))}
        </div>
      </div>
      <div className="flex items-center justify-center gap-2 mt-2">
        <span className="text-xs text-gray-500">{currentTip + 1} / {PRO_TIPS.length}</span>
      </div>
    </div>
  );
}