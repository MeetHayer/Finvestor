import { motion } from 'framer-motion';

export default function Watchlist() {
  return (
    <div className="container mx-auto px-6 py-8">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-3xl font-bold mb-6">Watchlist</h1>
      </motion.div>
      
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="card"
      >
        <p className="text-gray-600">Coming in next milestone...</p>
      </motion.div>
    </div>
  );
}





