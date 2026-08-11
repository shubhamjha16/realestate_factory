import React from 'react';
import { PortfolioRollup } from '../types';

interface PortfolioRollupViewProps {
  rollup: PortfolioRollup;
}

export const PortfolioRollupView: React.FC<PortfolioRollupViewProps> = ({ rollup }) => {
  return (
    <div className="bg-slate-950 text-slate-100 p-6 rounded-2xl border border-slate-800 space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-lg font-bold text-white">Portfolio Roll-Up & Concentration Summary</h3>
          <p className="text-xs text-slate-400">Multi-property asset value aggregation and concentration metrics.</p>
        </div>
        <div className="flex gap-4 font-mono text-xs">
          <div>
            <span className="text-slate-400 block text-[10px]">Properties</span>
            <span className="font-bold text-white text-sm">{rollup.total_properties}</span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px]">Total Asset Value</span>
            <span className="font-bold text-emerald-400 text-sm">₹{rollup.total_asset_value}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* City Concentration */}
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-3">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">City Concentration</h4>
          <div className="space-y-2">
            {rollup.concentration_by_city.map((c, idx) => (
              <div key={idx} className="flex justify-between items-center text-xs">
                <span className="text-slate-300">{c.name}</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-slate-400 text-[11px]">₹{c.value}</span>
                  <span className="font-mono font-bold text-indigo-400">{c.share_percentage}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Asset Class Concentration */}
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-3">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Asset Class Concentration</h4>
          <div className="space-y-2">
            {rollup.concentration_by_asset_class.map((c, idx) => (
              <div key={idx} className="flex justify-between items-center text-xs">
                <span className="text-slate-300">{c.name}</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-slate-400 text-[11px]">₹{c.value}</span>
                  <span className="font-mono font-bold text-emerald-400">{c.share_percentage}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Tenant Concentration */}
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-3">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Top Tenant Share</h4>
          <div className="space-y-2">
            {rollup.concentration_by_tenant.map((c, idx) => (
              <div key={idx} className="flex justify-between items-center text-xs">
                <span className="text-slate-300">{c.name}</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-slate-400 text-[11px]">₹{c.value}</span>
                  <span className="font-mono font-bold text-amber-400">{c.share_percentage}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
