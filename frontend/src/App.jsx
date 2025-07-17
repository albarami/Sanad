import React, { useState } from 'react';
import './App.css';

function App() {
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!query.trim()) {
      setError('Please enter a query');
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const res = await fetch('/api/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: query.trim() }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();
      setResponse(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatSanadScore = (score) => {
    if (typeof score !== 'number') return 'N/A';
    return (score * 100).toFixed(1) + '%';
  };

  const getScoreColor = (score) => {
    if (typeof score !== 'number') return 'text-gray-500';
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Sanad v2 Enterprise Verification System
          </h1>
          <p className="text-gray-600">
            AI-powered verification with Islamic scholarly methodology
          </p>
        </div>

        {/* Query Form */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-2">
                Enter your query for verification:
              </label>
              <textarea
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows="3"
                placeholder="e.g., What is the minimum wage in Qatar?"
                disabled={loading}
              />
            </div>
            
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Verifying...' : 'Verify Query'}
            </button>
          </form>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Response Display */}
        {response && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Verification Result</h2>
            
            {/* Sanad Score */}
            <div className="mb-4 p-4 bg-gray-50 rounded-md">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">Sanad Score:</span>
                <span className={`text-lg font-bold ${getScoreColor(response.sanad_score)}`}>
                  {formatSanadScore(response.sanad_score)}
                </span>
              </div>
            </div>

            {/* Answer */}
            <div className="mb-4">
              <h3 className="text-lg font-medium text-gray-900 mb-2">Answer:</h3>
              <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
                <p className="text-gray-800">{response.answer}</p>
              </div>
            </div>

            {/* Sources */}
            {response.sources && response.sources.length > 0 && (
              <div className="mb-4">
                <h3 className="text-lg font-medium text-gray-900 mb-2">Sources:</h3>
                <div className="space-y-2">
                  {response.sources.map((source, index) => (
                    <div key={index} className="bg-gray-50 p-3 rounded-md">
                      <div className="flex justify-between items-start mb-1">
                        <span className="text-sm font-medium text-gray-700">
                          {source.source || `Source ${index + 1}`}
                        </span>
                        <span className="text-xs text-gray-500">
                          Relevance: {((1 - (source.distance || 0)) * 100).toFixed(1)}%
                        </span>
                      </div>
                      <p className="text-sm text-gray-600">{source.content}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Agent Scores */}
            {response.agent_scores && (
              <div className="mb-4">
                <h3 className="text-lg font-medium text-gray-900 mb-2">Agent Analysis:</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(response.agent_scores).map(([agent, score]) => (
                    <div key={agent} className="bg-gray-50 p-3 rounded-md text-center">
                      <div className="text-sm font-medium text-gray-700 capitalize">
                        {agent.replace('_', ' ')}
                      </div>
                      <div className={`text-lg font-bold ${getScoreColor(score)}`}>
                        {formatSanadScore(score)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Raw JSON (for debugging) */}
            <details className="mt-4">
              <summary className="cursor-pointer text-sm text-gray-600 hover:text-gray-800">
                Show Raw Response
              </summary>
              <pre className="mt-2 p-4 bg-gray-100 rounded-md text-xs overflow-x-auto">
                {JSON.stringify(response, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
