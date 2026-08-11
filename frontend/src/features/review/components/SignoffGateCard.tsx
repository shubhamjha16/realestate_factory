import React, { useState } from 'react';
import { reviewService } from '../services/reviewService';
import { SignoffResponse } from '../types';
import { messageFor } from '@/global/errors';

interface SignoffGateCardProps {
  deliverableId: string;
  currentStatus: string;
  openNotesCount: number;
  onSignedSuccess?: (resp: SignoffResponse) => void;
}

export const SignoffGateCard: React.FC<SignoffGateCardProps> = ({
  deliverableId,
  currentStatus,
  openNotesCount,
  onSignedSuccess,
}) => {
  const [assetClass, setAssetClass] = useState<string>('land_and_building');
  const [signing, setSigning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [signedData, setSignedData] = useState<SignoffResponse | null>(null);

  const isSigned = currentStatus === 'signed' || signedData !== null;

  const handleSign = async () => {
    try {
      setSigning(true);
      setError(null);
      const res = await reviewService.signDeliverable(deliverableId, assetClass);
      setSignedData(res);
      if (onSignedSuccess) onSignedSuccess(res);
    } catch (err: unknown) {
      setError(messageFor(err));
    } finally {
      setSigning(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <h3 className="text-base font-bold text-white uppercase tracking-wider">The Sign-Off Gate</h3>
        <span
          className={`px-3 py-1 text-xs font-bold rounded-full ${
            isSigned
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
              : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
          }`}
        >
          {isSigned ? 'SIGNED & SEALED' : 'DRAFT — NOT FOR RELIANCE'}
        </span>
      </div>

      {isSigned ? (
        <div className="p-4 bg-emerald-950/40 border border-emerald-800/60 rounded-xl space-y-2">
          <p className="text-sm font-semibold text-emerald-300">Deliverable Signed & Sealed</p>
          <p className="text-xs text-slate-300">
            Signer User ID: <span className="font-mono text-emerald-400">{signedData?.signed_by}</span>
          </p>
          <p className="text-xs text-slate-400">Signed At: {signedData?.signed_at}</p>
          <p className="text-[11px] text-emerald-400 italic">
            Draft watermark removed. Report certified for client reliance.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-xs text-slate-300 leading-relaxed">
            Signing certifies this valuation report. Requires an active IBBI Registration Number matching the asset class and zero open review notes.
          </p>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Registered Asset Class</label>
            <select
              value={assetClass}
              onChange={(e) => setAssetClass(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200"
            >
              <option value="land_and_building">Land & Building</option>
              <option value="plant_and_machinery">Plant & Machinery</option>
              <option value="securities_or_financial_assets">Securities or Financial Assets</option>
            </select>
          </div>

          {error && (
            <div className="p-3 bg-red-950/80 border border-red-800 text-red-300 rounded-lg text-xs font-mono">
              {error}
            </div>
          )}

          <button
            onClick={handleSign}
            disabled={signing || openNotesCount > 0}
            className={`w-full py-3 text-xs font-bold uppercase tracking-wider rounded-xl transition ${
              openNotesCount > 0
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/30'
            }`}
          >
            {signing
              ? 'Verifying Sign-Off Gate...'
              : openNotesCount > 0
              ? `Sign-Off Blocked (${openNotesCount} Open Note(s))`
              : 'Sign Valuation Report (IBBI Valuer / Partner)'}
          </button>
        </div>
      )}
    </div>
  );
};
