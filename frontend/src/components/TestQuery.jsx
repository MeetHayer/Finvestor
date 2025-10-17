import { useWatchlists } from '../lib/queries';

export default function TestQuery() {
  const { data, isLoading, error } = useWatchlists();
  
  return (
    <div className="p-4 bg-blue-50 border border-blue-200 rounded">
      <h3 className="font-bold text-blue-800">Query Test</h3>
      <p>Loading: {isLoading ? 'Yes' : 'No'}</p>
      <p>Error: {error ? error.message : 'None'}</p>
      <p>Data: {data ? JSON.stringify(data).substring(0, 100) + '...' : 'No data'}</p>
    </div>
  );
}




