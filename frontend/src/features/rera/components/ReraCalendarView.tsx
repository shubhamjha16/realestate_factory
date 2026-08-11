import React, { useState } from 'react';
import { reraService } from '../services/reraService';
import { ReraObligation } from '../types';
import { messageFor } from '@/global/errors';

export const ReraCalendarView: React.FC = () => {
  const [state, setState] = useState<string>('maharashtra');
  const [regDate, setRegDate] = useState<string>('2025-01-15');
  const [endDate, setEndDate] = useState<string>('2027-12-31');
  const [obligations, setObligations] = useState<ReraObligation[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      const data = await reraService.fetchObligations(state, regDate, endDate);
      setObligations(data);
    } catch (err: unknown) {
      setError(messageFor(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-950 text-slate-100 p-6 rounded-2xl border border-slate-800 space-y-6">
      <div className="border-b border-slate-800 pb-4">
        <h3 className="text-lg font-bold text-white">RERA Quarterly Obligations Calendar</h3>
        <p className="text-xs text-slate-400">
          Notified state authority quarterly progress report (QPR) due-date schedule engine.
        </p>
      </div>

      <form onSubmit={handleGenerate} className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div>
          <label className="block text-xs text-slate-400 mb-1">State Authority</label>
          <select
            value={state}
            onChange={(e) => setState(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200"
          >
            <option value="maharashtra">Maharashtra (MahaRERA)</option>
            <option value="karnataka">Karnataka (K-RERA)</option>
            <option value="delhi">Delhi RERA</option>
            <option value="uttar_pradesh">Uttar Pradesh (UP RERA)</option>
          </select>
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">Registration Date</label>
          <input
            type="date"
            value={regDate}
            onChange={(e) => setRegDate(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
          />
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">Estimated Completion Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
          />
        </div>

        <div className="flex items-end">
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
          >
            {loading ? 'Generating...' : 'Generate Calendar'}
          </button>
        </div>
      </form>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {obligations.length > 0 && (
        <div className="space-y-3">
          <div className="flex justify-between items-center text-xs text-slate-400 font-mono">
            <span>Authority: {obligations[0]?.authority}</span>
            <span>Total QPR Filings: {obligations.length}</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-96 overflow-y-auto pr-1">
            {obligations.map((ob, idx) => (
              <div
                key={idx}
                className="p-3.5 bg-slate-900/60 border border-slate-800/80 rounded-xl flex items-center justify-between"
              >
                <div>
                  <h4 className="font-semibold text-xs text-white">{ob.period}</h4>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Filing Due Date: <span className="font-mono text-emerald-400">{ob.due_date}</span>
                  </p>
                </div>
                <span
                  className={`px-2.5 py-0.5 text-[10px] font-bold rounded-full border uppercase ${
                    ob.status === 'completed'
                      ? 'bg-slate-800 text-slate-400 border-slate-700'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                  }`}
                >
                  {ob.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
