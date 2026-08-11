import React, { useState } from 'react';
import { reraService } from '../services/reraService';
import { StampDutyCalculation } from '../types';
import { messageFor } from '@/global/errors';

export const StampDutyCalculator: React.FC = () => {
  const [state, setState] = useState<string>('maharashtra');
  const [consideration, setConsideration] = useState<number>(25000000);
  const [circleRate, setCircleRate] = useState<number>(18000);
  const [area, setArea] = useState<number>(1500);
  const [gender, setGender] = useState<string>('male');
  const [result, setResult] = useState<StampDutyCalculation | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      const data = await reraService.calculateStampDuty(state, consideration, circleRate, area, 'sale_deed', gender);
      setResult(data);
    } catch (err: unknown) {
      setError(messageFor(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-950 text-slate-100 p-6 rounded-2xl border border-slate-800 space-y-6">
      <div className="border-b border-slate-800 pb-4">
        <h3 className="text-lg font-bold text-white">Stamp Duty & Circle Rate Floor Calculator</h3>
        <p className="text-xs text-slate-400">
          Enforces statutory rule: Taxable Value = max(Agreed Consideration, Circle Rate Valuation).
        </p>
      </div>

      <form onSubmit={handleCalculate} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label className="block text-xs text-slate-400 mb-1">State Jurisdiction</label>
          <select
            value={state}
            onChange={(e) => setState(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
          >
            <option value="maharashtra">Maharashtra</option>
            <option value="delhi">Delhi</option>
            <option value="karnataka">Karnataka</option>
            <option value="uttar_pradesh">Uttar Pradesh</option>
          </select>
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">Agreed Consideration (₹)</label>
          <input
            type="number"
            value={consideration}
            onChange={(e) => setConsideration(Number(e.target.value))}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
          />
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">Circle Rate (₹ / sqft)</label>
          <input
            type="number"
            value={circleRate}
            onChange={(e) => setCircleRate(Number(e.target.value))}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
          />
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">Property Area (sqft)</label>
          <input
            type="number"
            value={area}
            onChange={(e) => setArea(Number(e.target.value))}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
          />
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">Transferee Gender</label>
          <select
            value={gender}
            onChange={(e) => setGender(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
          >
            <option value="male">Male</option>
            <option value="female">Female</option>
          </select>
        </div>

        <div className="flex items-end">
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
          >
            {loading ? 'Calculating...' : 'Compute Dues'}
          </button>
        </div>
      </form>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {result && (
        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-3">
          <div className="flex justify-between items-center pb-2 border-b border-slate-800">
            <span className="text-xs font-semibold text-slate-300">Applied Taxable Basis:</span>
            <span
              className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded border ${
                result.applied_basis === 'circle_rate_floor'
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                  : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
              }`}
            >
              {result.applied_basis.replace(/_/g, ' ')}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div>
              <span className="text-[10px] text-slate-400 block">Circle Valuation</span>
              <span className="font-mono text-slate-200">₹{result.circle_valuation}</span>
            </div>

            <div>
              <span className="text-[10px] text-slate-400 block">Taxable Consideration</span>
              <span className="font-mono text-emerald-400 font-bold">₹{result.taxable_value}</span>
            </div>

            <div>
              <span className="text-[10px] text-slate-400 block">Stamp Duty ({Number(result.stamp_duty_rate) * 100}%)</span>
              <span className="font-mono text-indigo-300">₹{result.stamp_duty_amount}</span>
            </div>

            <div>
              <span className="text-[10px] text-slate-400 block">Total Statutory Dues</span>
              <span className="font-mono text-emerald-400 font-bold text-sm">₹{result.total_statutory_dues}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
