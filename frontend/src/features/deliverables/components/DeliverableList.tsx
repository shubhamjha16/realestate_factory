import React, { useState, useEffect } from 'react';
import { deliverableService } from '../services/deliverableService';
import { DeliverableSummary } from '../types';
import { ProvenanceView } from './ProvenanceView';

interface DeliverableListProps {
  mandateId?: string;
}

export const DeliverableList: React.FC<DeliverableListProps> = ({ mandateId }) => {
  const [deliverables, setDeliverables] = useState<DeliverableSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeProvenanceId, setActiveProvenanceId] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    deliverableService
      .listDeliverables(mandateId)
      .then((data) => {
        if (isMounted) {
          setDeliverables(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to load deliverables');
          setLoading(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, [mandateId]);

  if (activeProvenanceId) {
    return (
      <ProvenanceView
        deliverableId={activeProvenanceId}
        onClose={() => setActiveProvenanceId(null)}
      />
    );
  }

  return (
    <div className="bg-slate-900 text-slate-100 p-6 rounded-2xl border border-slate-800 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-white">Generated Mandate Deliverables</h2>
        <span className="text-xs text-slate-400 font-mono">{deliverables.length} Deliverable(s)</span>
      </div>

      {loading && <p className="text-xs text-slate-400">Loading deliverables...</p>}
      {error && <p className="text-xs text-red-400">{error}</p>}

      {!loading && deliverables.length === 0 && (
        <p className="text-xs text-slate-500 py-6 text-center">No deliverables found for this mandate.</p>
      )}

      {!loading && deliverables.length > 0 && (
        <div className="space-y-2">
          {deliverables.map((deliv) => (
            <div
              key={deliv.id}
              className="p-4 bg-slate-950/60 border border-slate-800/80 rounded-xl flex items-center justify-between hover:border-slate-700 transition"
            >
              <div>
                <h4 className="font-semibold text-sm text-white">{deliv.title}</h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Type: {deliv.doc_type} | Status:{' '}
                  <span className="font-mono text-emerald-400 capitalize">{deliv.status}</span>
                </p>
              </div>
              <button
                onClick={() => setActiveProvenanceId(deliv.id)}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition shadow-lg shadow-indigo-600/20"
              >
                Inspect Provenance
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
