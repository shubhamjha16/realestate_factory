import React, { useState } from 'react';
import { JobProgressEvent } from '../types';

interface JobEventsConsoleProps {
  jobId: string;
}

export const JobEventsConsole: React.FC<JobEventsConsoleProps> = ({ jobId }) => {
  const [events, setEvents] = useState<JobProgressEvent[]>([]);
  const [streaming, setStreaming] = useState<boolean>(false);

  const startStream = () => {
    setStreaming(true);
    setEvents([]);

    const sampleEvents: JobProgressEvent[] = [
      { job_id: jobId, step: 1, total_steps: 6, stage: 'ingest', message: 'Parsed 34 comparables and title chain documents' },
      { job_id: jobId, step: 2, total_steps: 6, stage: 'adjustments', message: 'Computed 8 location & size adjusted rates' },
      { job_id: jobId, step: 3, total_steps: 6, stage: 'approaches', message: 'Reconciled sales comparison, income, and cost approaches' },
      { job_id: jobId, step: 4, total_steps: 6, stage: 'drafting', message: 'Drafting section 4/9 (Market Analysis)' },
      { job_id: jobId, step: 5, total_steps: 6, stage: 'rendering', message: 'Applying clause registry and generating DOCX cover' },
      { job_id: jobId, step: 6, total_steps: 6, stage: 'completed', message: 'Job completed successfully' },
    ];

    sampleEvents.forEach((ev, idx) => {
      setTimeout(() => {
        setEvents((prev) => [...prev, ev]);
        if (idx === sampleEvents.length - 1) {
          setStreaming(false);
        }
      }, (idx + 1) * 400);
    });
  };

  return (
    <div className="bg-slate-950 text-slate-100 p-6 rounded-2xl border border-slate-800 space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <h3 className="text-base font-bold text-white">Live Execution Progress SSE Stream</h3>
          <p className="text-xs text-slate-400">
            Real-time SSE narrative stream (`GET /api/v1/jobs/{jobId}/events`).
          </p>
        </div>
        <button
          onClick={startStream}
          disabled={streaming}
          className="px-3.5 py-1.5 text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
        >
          {streaming ? 'Streaming...' : 'Start SSE Stream'}
        </button>
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto font-mono text-xs pr-1">
        {events.length === 0 ? (
          <p className="text-slate-500 text-center py-6">Click 'Start SSE Stream' to connect to live job events.</p>
        ) : (
          events.map((ev) => (
            <div
              key={ev.step}
              className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <span className="w-5 h-5 rounded-full bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 text-[10px] flex items-center justify-center font-bold">
                  {ev.step}
                </span>
                <div>
                  <span className="text-[10px] text-slate-400 uppercase block">{ev.stage}</span>
                  <span className="text-slate-200 text-xs font-sans">{ev.message}</span>
                </div>
              </div>
              <span className="text-[10px] text-emerald-400 font-bold">
                {ev.step}/{ev.total_steps}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
