import React, { useState } from 'react';
import { portfolioService } from '../services/portfolioService';
import { DisbursementCheck } from '../types';

export const DisbursementCheckCard: React.FC = () => {
  const [certifiedStage, setCertifiedStage] = useState<number>(65);
  const [priorDisbursed, setPriorDisbursed] = useState<number>(50);
  const [requestedTranche, setRequestedTranche] = useState<number>(20);
  const [result, setResult] = useState<DisbursementCheck | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const res = await portfolioService.verifyDisbursement(certifiedStage, requestedTranche, priorDisbursed);
      setResult(res);
    } catch (err: unknown) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-950 text-slate-100 p-6 rounded-2xl border border-slate-800 space-y-4">
      <div className="border-b border-slate-800 pb-3">
        <h3 className="text-base font-bold text-white">Construction Disbursement Stage Gate</h3>
        <p className="text-xs text-slate-400">Verifies tranche request against certified physical progress percentage.</p>
      </div>

      <form onSubmit={handleVerify} className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div>
          <label className="block text-xs text-slate-400 mb-1">Certified Physical Stage (%)</label>
          <input
            type="number"
            value={certifiedStage}
            onChange={(e) => setCertifiedStage(Number(e.target.value))}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
          />
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">Prior Disbursed (%)</label>
          <input
            type="number"
            value={priorDisbursed}
            onChange={(e) => setPriorDisbursed(Number(e.target.value))}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
          />
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">Requested Tranche (%)</label>
          <input
            type="number"
            value={requestedTranche}
            onChange={(e) => setRequestedTranche(Number(e.target.value))}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
          />
        </div>

        <div className="flex items-end">
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
          >
            {loading ? 'Verifying...' : 'Verify Stage Gate'}
          </button>
        </div>
      </form>

      {result && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between transition ${
            result.approved
              ? 'bg-emerald-950/40 border-emerald-800/80 text-emerald-200'
              : 'bg-red-950/40 border-red-800/80 text-red-200'
          }`}
        >
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider block font-mono">
              Status: {result.status_code}
            </span>
            <p className="text-xs mt-1 leading-relaxed font-medium">{result.message}</p>
          </div>

          <span
            className={`px-3 py-1 text-xs font-bold rounded-full uppercase border ${
              result.approved
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                : 'bg-red-500/20 text-red-300 border-red-500/40'
            }`}
          >
            {result.approved ? 'APPROVED' : 'PAYMENT BLOCKED'}
          </span>
        </div>
      )}
    </div>
  );
};
