import React from 'react';
import { ExpiringApproval } from '../types';

interface ApprovalsTrackerProps {
  approvals: ExpiringApproval[];
}

export const ApprovalsTracker: React.FC<ApprovalsTrackerProps> = ({ approvals }) => {
  return (
    <div className="bg-slate-950 text-slate-100 p-6 rounded-2xl border border-slate-800 space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <h3 className="text-base font-bold text-white">Statutory Approvals & NOC Expiry Tracker</h3>
          <p className="text-xs text-slate-400">Monitoring CC, OC, Fire NOC, and Environment NOC 90-day validity windows.</p>
        </div>
        <span className="text-xs font-mono px-2.5 py-1 bg-slate-900 border border-slate-800 rounded-lg text-slate-300">
          {approvals.length} Approval(s) Flagged
        </span>
      </div>

      {approvals.length === 0 ? (
        <p className="text-xs text-slate-500 text-center py-6">All statutory approvals are valid and outside 90-day expiry window.</p>
      ) : (
        <div className="space-y-2">
          {approvals.map((app, idx) => (
            <div
              key={idx}
              className={`p-3.5 rounded-xl border flex items-center justify-between transition ${
                app.is_expired
                  ? 'bg-red-950/40 border-red-800/80 text-red-200'
                  : 'bg-amber-950/40 border-amber-800/80 text-amber-200'
              }`}
            >
              <div>
                <h4 className="font-semibold text-xs text-white uppercase">{app.kind}</h4>
                <p className="text-[11px] text-slate-300 mt-0.5">
                  Authority: {app.issuing_authority} | Valid Until: <span className="font-mono">{app.valid_until}</span>
                </p>
              </div>

              <span
                className={`px-3 py-1 text-xs font-bold rounded-full uppercase border ${
                  app.is_expired
                    ? 'bg-red-500/20 text-red-400 border-red-500/40'
                    : 'bg-amber-500/20 text-amber-400 border-amber-500/40'
                }`}
              >
                {app.status_warning}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
