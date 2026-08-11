import React from 'react';
import { RentRollSummary } from '../types';

interface RentRollWaultCardProps {
  summary: RentRollSummary;
}

export const RentRollWaultCard: React.FC<RentRollWaultCardProps> = ({ summary }) => {
  return (
    <div className="bg-slate-950 text-slate-100 p-6 rounded-2xl border border-slate-800 space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-lg font-bold text-white">Rent Roll Depth & WAULT Analysis</h3>
          <p className="text-xs text-slate-400">As of {summary.as_of_date} | Leased Area: {summary.total_leased_area_sqft} sqft</p>
        </div>
        <div className="text-right">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Portfolio WAULT</span>
          <span className="text-xl font-bold font-mono text-indigo-400">{summary.wault_years} Years</span>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl">
          <span className="text-[10px] text-slate-400 block font-medium">Monthly Rent</span>
          <span className="text-sm font-bold font-mono text-emerald-400">₹{summary.total_monthly_rent}</span>
        </div>

        <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl">
          <span className="text-[10px] text-slate-400 block font-medium">Annual Rent</span>
          <span className="text-sm font-bold font-mono text-emerald-400">₹{summary.total_annual_rent}</span>
        </div>

        <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl">
          <span className="text-[10px] text-slate-400 block font-medium">Active Leases</span>
          <span className="text-sm font-bold font-mono text-slate-200">{summary.total_active_leases} Leases</span>
        </div>

        <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl">
          <span className="text-[10px] text-slate-400 block font-medium">Total Leased Area</span>
          <span className="text-sm font-bold font-mono text-slate-200">{summary.total_leased_area_sqft} sqft</span>
        </div>
      </div>

      {/* Expiry Profile */}
      <div className="space-y-2">
        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Lease Expiry Profile</h4>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
          {Object.entries(summary.expiry_profile).map(([key, val]) => (
            <div key={key} className="p-3 bg-slate-900/40 border border-slate-800/80 rounded-lg space-y-1">
              <span className="text-[10px] font-mono text-slate-400 block capitalize">{key.replace(/_/g, ' ')}</span>
              <div className="flex justify-between items-center">
                <span className="font-bold text-slate-200">{val.count} Lease(s)</span>
                <span className="font-mono text-emerald-400 font-semibold">₹{val.annual_rent}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
