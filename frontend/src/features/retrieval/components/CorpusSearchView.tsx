import React, { useState } from 'react';
import { retrievalService } from '../services/retrievalService';
import { CorpusSearchResponse } from '../types';

interface CorpusSearchViewProps {
  currentFirmId: string;
}

export const CorpusSearchView: React.FC<CorpusSearchViewProps> = ({ currentFirmId }) => {
  const [targetFirmId, setTargetFirmId] = useState<string>(currentFirmId);
  const [locality, setLocality] = useState<string>('BKC');
  const [response, setResponse] = useState<CorpusSearchResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const res = await retrievalService.searchCorpus(targetFirmId, locality);
      setResponse(res);
    } catch (err: unknown) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-950 text-slate-100 p-6 rounded-2xl border border-slate-800 space-y-6">
      <div className="border-b border-slate-800 pb-4">
        <h3 className="text-lg font-bold text-white">House Wording Corpus Retrieval</h3>
        <p className="text-xs text-slate-400">
          Search past firm valuation reports for locality commentary and house wording (Firm-scoped, commentary-only).
        </p>
      </div>

      <form onSubmit={handleSearch} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label className="block text-xs text-slate-400 mb-1">Target Firm ID</label>
          <input
            type="text"
            value={targetFirmId}
            onChange={(e) => setTargetFirmId(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs font-mono text-slate-200"
          />
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">Locality Keyword</label>
          <input
            type="text"
            value={locality}
            onChange={(e) => setLocality(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
          />
        </div>

        <div className="flex items-end">
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
          >
            {loading ? 'Searching Corpus...' : 'Search House Wording'}
          </button>
        </div>
      </form>

      {response && (
        <div className="space-y-4">
          {response.audit_logged && (
            <div className="p-4 bg-red-950/40 border border-red-800/80 rounded-xl space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-red-400 font-mono">
                SECURITY VIOLATION DETECTED & LOGGED
              </span>
              <p className="text-xs text-red-200">{response.error}</p>
            </div>
          )}

          {!response.audit_logged && (
            <div className="space-y-3">
              <span className="text-xs font-semibold text-slate-400">
                Retrieved Snippets ({response.results.length} match(es))
              </span>
              {response.results.map((res) => (
                <div key={res.id} className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-white">
                      Locality: {res.locality} ({res.city})
                    </span>
                    <span className="px-2 py-0.5 bg-slate-800 text-indigo-300 font-mono text-[10px] rounded">
                      {res.topic}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 italic bg-slate-950/40 p-3 rounded-lg border border-slate-800/60">
                    "{res.content}"
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
