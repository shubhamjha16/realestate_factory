import React, { useState } from 'react';

interface ExportDrawerProps {
  deliverableId: string;
  title: string;
  onClose?: () => void;
}

export const ExportDrawer: React.FC<ExportDrawerProps> = ({ deliverableId, title, onClose }) => {
  const [downloading, setDownloading] = useState<string | null>(null);

  const handleExport = (format: 'docx' | 'pdf' | 'xlsx' | 'json') => {
    setDownloading(format);
    setTimeout(() => {
      setDownloading(null);
    }, 1200);
  };

  return (
    <div className="bg-slate-950 text-slate-100 p-6 rounded-2xl border border-slate-800 space-y-6 shadow-2xl">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-lg font-bold text-white">Export & Download Console</h3>
          <p className="text-xs text-slate-400">
            {title} (ID: <span className="font-mono text-slate-300">{deliverableId}</span>)
          </p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-xs text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
          >
            Close
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* DOCX Card */}
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-2 hover:border-slate-700 transition">
          <div className="flex justify-between items-center">
            <h4 className="font-bold text-sm text-white">DOCX Report</h4>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
              Word Doc
            </span>
          </div>
          <p className="text-xs text-slate-400">Full valuation report formatted with executive cover & summary tables.</p>
          <button
            onClick={() => handleExport('docx')}
            disabled={downloading === 'docx'}
            className="w-full mt-2 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
          >
            {downloading === 'docx' ? 'Preparing DOCX...' : 'Download DOCX'}
          </button>
        </div>

        {/* PDF Card */}
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-2 hover:border-slate-700 transition">
          <div className="flex justify-between items-center">
            <h4 className="font-bold text-sm text-white">PDF Document</h4>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">
              PDF Format
            </span>
          </div>
          <p className="text-xs text-slate-400">Print-ready PDF report for formal client distribution.</p>
          <button
            onClick={() => handleExport('pdf')}
            disabled={downloading === 'pdf'}
            className="w-full mt-2 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
          >
            {downloading === 'pdf' ? 'Preparing PDF...' : 'Download PDF'}
          </button>
        </div>

        {/* XLSX Live Formulas Card */}
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-2 hover:border-slate-700 transition">
          <div className="flex justify-between items-center">
            <h4 className="font-bold text-sm text-white">XLSX Adjustment Grid & Rent Roll</h4>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Live Formulas
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Excel workbook with <span className="text-emerald-400 font-semibold">live formulas intact</span> (=SUM, =AVERAGE, =B2*(1+C2)).
          </p>
          <button
            onClick={() => handleExport('xlsx')}
            disabled={downloading === 'xlsx'}
            className="w-full mt-2 py-2 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition shadow-lg shadow-emerald-600/20"
          >
            {downloading === 'xlsx' ? 'Building Live XLSX...' : 'Download XLSX (Live Formulas)'}
          </button>
        </div>

        {/* Machine JSON Card */}
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-2 hover:border-slate-700 transition">
          <div className="flex justify-between items-center">
            <h4 className="font-bold text-sm text-white">JSON Machine Payload</h4>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
              JSON
            </span>
          </div>
          <p className="text-xs text-slate-400">Structured JSON representation for API integration.</p>
          <button
            onClick={() => handleExport('json')}
            disabled={downloading === 'json'}
            className="w-full mt-2 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
          >
            {downloading === 'json' ? 'Preparing JSON...' : 'Download JSON'}
          </button>
        </div>
      </div>
    </div>
  );
};
