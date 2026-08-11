import React, { useState } from 'react';
import { useProvenance } from '../hooks/useProvenance';
import { FigureProvenance, DocumentProvenance, ProvenanceSection } from '../types';

interface ProvenanceViewProps {
  deliverableId: string;
  onClose?: () => void;
}

export const ProvenanceView: React.FC<ProvenanceViewProps> = ({ deliverableId, onClose }) => {
  const { provenance, loading, error } = useProvenance(deliverableId);
  const [selectedFigure, setSelectedFigure] = useState<FigureProvenance | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<DocumentProvenance | null>(null);

  if (loading) {
    return (
      <div className="p-8 text-center bg-slate-900 text-slate-100 rounded-xl shadow-2xl border border-slate-800">
        <div className="animate-spin w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-slate-400 font-medium">Resolving complete provenance chain (Figures → Comparables, Facts → Documents)...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-950/80 border border-red-800 text-red-200 rounded-xl">
        <h3 className="font-semibold text-lg mb-2">Provenance Resolution Error</h3>
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  if (!provenance) return null;

  return (
    <div className="bg-slate-950 text-slate-100 p-6 rounded-2xl border border-slate-800 shadow-2xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center space-x-3">
            <h2 className="text-xl font-bold text-white tracking-wide">{provenance.title}</h2>
            <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Audited & Traced
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deliverable ID: <span className="font-mono text-slate-300">{provenance.deliverable_id}</span> | Type: {provenance.doc_type}
          </p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
          >
            Close
          </button>
        )}
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sections List */}
        <div className="lg:col-span-2 space-y-4 max-h-[600px] overflow-y-auto pr-2">
          {provenance.sections.map((sec: ProvenanceSection) => (
            <div
              key={sec.section_id}
              className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl hover:border-slate-700 transition"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  Section #{sec.ord} ({sec.section_type})
                </span>
                <div className="flex space-x-2">
                  {sec.figures.length > 0 && (
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      {sec.figures.length} Figure Line(s)
                    </span>
                  )}
                  {sec.documents.length > 0 && (
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      {sec.documents.length} Doc Evidence
                    </span>
                  )}
                </div>
              </div>

              <p className="text-sm text-slate-300 line-clamp-3 mb-3 leading-relaxed">
                {sec.content}
              </p>

              {/* Provenance Badges */}
              <div className="space-y-2 pt-2 border-t border-slate-800/50">
                {sec.figures.map((fig) => (
                  <button
                    key={fig.valuation_line_id}
                    onClick={() => { setSelectedFigure(fig); setSelectedDocument(null); }}
                    className={`w-full text-left p-2 rounded-lg text-xs flex items-center justify-between transition ${
                      selectedFigure?.valuation_line_id === fig.valuation_line_id
                        ? 'bg-indigo-600/30 border border-indigo-500 text-indigo-200'
                        : 'bg-slate-800/40 hover:bg-slate-800/80 text-slate-300 border border-slate-800'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold">{fig.label}:</span>
                      <span className="font-mono text-emerald-400">₹{fig.amount}</span>
                    </div>
                    <span className="text-[10px] text-indigo-400">Inspect Chain →</span>
                  </button>
                ))}

                {sec.documents.map((doc) => (
                  <button
                    key={doc.document_id}
                    onClick={() => { setSelectedDocument(doc); setSelectedFigure(null); }}
                    className={`w-full text-left p-2 rounded-lg text-xs flex items-center justify-between transition ${
                      selectedDocument?.document_id === doc.document_id
                        ? 'bg-amber-600/30 border border-amber-500 text-amber-200'
                        : 'bg-slate-800/40 hover:bg-slate-800/80 text-slate-300 border border-slate-800'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold uppercase text-amber-400">{doc.kind}</span>
                      <span className="text-slate-400">Auth: {doc.issuing_authority || 'N/A'}</span>
                    </div>
                    <span className="text-[10px] text-amber-400">Inspect Evidence →</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Provenance Detail Drawer / Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800 pb-2">
            Provenance Inspector
          </h3>

          {selectedFigure && (
            <div className="space-y-3">
              <div className="p-3 bg-indigo-950/40 border border-indigo-800/60 rounded-lg">
                <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">Valuation Line</span>
                <h4 className="font-semibold text-white text-base mt-1">{selectedFigure.label}</h4>
                <p className="text-lg font-mono text-emerald-400 font-bold mt-1">₹{selectedFigure.amount}</p>
                {selectedFigure.basis && (
                  <p className="text-xs text-slate-400 mt-1">Basis: {selectedFigure.basis}</p>
                )}
              </div>

              <div>
                <h5 className="text-xs font-semibold text-slate-300 mb-2">Backing Comparables ({selectedFigure.comparables.length})</h5>
                {selectedFigure.comparables.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">No direct comparables attached.</p>
                ) : (
                  <div className="space-y-2">
                    {selectedFigure.comparables.map((comp) => (
                      <div key={comp.comparable_id} className="p-2.5 bg-slate-800/60 rounded-lg border border-slate-800 text-xs">
                        <p className="font-medium text-slate-200">{comp.address}</p>
                        <div className="flex justify-between text-slate-400 mt-1 text-[11px]">
                          <span>Sale: ₹{comp.sale_price || 'N/A'}</span>
                          <span>Rate: ₹{comp.rate_per_unit}/sqft</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {selectedDocument && (
            <div className="space-y-3">
              <div className="p-3 bg-amber-950/40 border border-amber-800/60 rounded-lg">
                <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Document Evidence</span>
                <h4 className="font-semibold text-white text-base mt-1 uppercase">{selectedDocument.kind}</h4>
                <p className="text-xs text-slate-300 mt-1">Issuing Authority: {selectedDocument.issuing_authority || 'N/A'}</p>
                {selectedDocument.doc_date && (
                  <p className="text-xs text-slate-400 mt-1">Dated: {selectedDocument.doc_date}</p>
                )}
              </div>

              {selectedDocument.s3_key && (
                <div className="p-3 bg-slate-800/60 rounded-lg border border-slate-800 text-xs">
                  <span className="text-slate-400 block mb-1">Registered S3 Location:</span>
                  <code className="text-[10px] font-mono text-emerald-400 break-all">{selectedDocument.s3_key}</code>
                </div>
              )}
            </div>
          )}

          {!selectedFigure && !selectedDocument && (
            <div className="text-center py-12 text-slate-500 text-xs">
              Select any figure line or document evidence badge on the left to inspect its complete underlying chain.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
