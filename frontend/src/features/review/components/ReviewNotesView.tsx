import React, { useState, useEffect } from 'react';
import { reviewService } from '../services/reviewService';
import { ReviewNote } from '../types';
import { messageFor } from '@/global/errors';

interface ReviewNotesViewProps {
  deliverableId: string;
  onNotesChange?: (openCount: number) => void;
}

export const ReviewNotesView: React.FC<ReviewNotesViewProps> = ({ deliverableId, onNotesChange }) => {
  const [notes, setNotes] = useState<ReviewNote[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [newNoteText, setNewNoteText] = useState<string>('');
  const [activeResponseId, setActiveResponseId] = useState<string | null>(null);
  const [responseText, setResponseText] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const fetchNotes = async () => {
    try {
      setLoading(true);
      const data = await reviewService.listNotes(deliverableId);
      setNotes(data);
      const openCount = data.filter((n) => n.status !== 'closed').length;
      if (onNotesChange) onNotesChange(openCount);
      setError(null);
    } catch (err: unknown) {
      setError(messageFor(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotes();
  }, [deliverableId]);

  const handleCreateNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNoteText.trim()) return;
    try {
      await reviewService.createNote(deliverableId, { note: newNoteText });
      setNewNoteText('');
      await fetchNotes();
    } catch (err: unknown) {
      setError(messageFor(err));
    }
  };

  const handleRespond = async (noteId: string) => {
    if (!responseText.trim()) return;
    try {
      await reviewService.respondNote(noteId, responseText);
      setActiveResponseId(null);
      setResponseText('');
      await fetchNotes();
    } catch (err: unknown) {
      setError(messageFor(err));
    }
  };

  const handleClose = async (noteId: string) => {
    try {
      await reviewService.closeNote(noteId);
      await fetchNotes();
    } catch (err: unknown) {
      setError(messageFor(err));
    }
  };

  const openNotesCount = notes.filter((n) => n.status !== 'closed').length;

  return (
    <div className="bg-slate-950 text-slate-100 p-6 rounded-2xl border border-slate-800 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            Review Notes & Collaboration Thread
          </h3>
          <p className="text-xs text-slate-400">
            Valuer review notes must be responded to and closed prior to deliverable sign-off.
          </p>
        </div>
        <span
          className={`px-3 py-1 text-xs font-semibold rounded-full border ${
            openNotesCount > 0
              ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
              : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
          }`}
        >
          {openNotesCount > 0 ? `${openNotesCount} Open Note(s) Blocking Sign-off` : 'Zero Open Notes'}
        </span>
      </div>

      {error && (
        <div className="p-3 bg-red-950/80 border border-red-800 text-red-300 rounded-lg text-xs">
          {error}
        </div>
      )}

      {/* New Note Form */}
      <form onSubmit={handleCreateNote} className="space-y-3">
        <textarea
          value={newNoteText}
          onChange={(e) => setNewNoteText(e.target.value)}
          placeholder="Raise a new review note (e.g. 'Verify cap rate basis in section 3')..."
          rows={2}
          className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
        />
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={!newNoteText.trim()}
            className="px-4 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition disabled:opacity-50"
          >
            Raise Review Note
          </button>
        </div>
      </form>

      {/* Notes List */}
      <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
        {loading && <p className="text-xs text-slate-400">Loading notes...</p>}
        {!loading && notes.length === 0 && (
          <p className="text-xs text-slate-500 text-center py-6">No review notes raised yet.</p>
        )}

        {notes.map((n) => (
          <div
            key={n.id}
            className={`p-4 rounded-xl border transition ${
              n.status === 'open'
                ? 'bg-slate-900/80 border-amber-500/40'
                : n.status === 'responded'
                ? 'bg-slate-900/80 border-indigo-500/40'
                : 'bg-slate-900/40 border-slate-800 text-slate-400'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800">
                Status: {n.status}
              </span>
              <span className="text-[10px] text-slate-500">{n.created_at?.slice(0, 10)}</span>
            </div>

            <p className="text-xs text-slate-200 leading-relaxed font-medium mb-3">{n.note}</p>

            {n.response && (
              <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-xs mb-3">
                <span className="text-[10px] font-bold text-indigo-400 block mb-1">Analyst Response:</span>
                <p className="text-slate-300">{n.response}</p>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800/50">
              {n.status !== 'closed' && (
                <>
                  {activeResponseId !== n.id ? (
                    <button
                      onClick={() => setActiveResponseId(n.id)}
                      className="px-2.5 py-1 text-[11px] font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition"
                    >
                      Respond
                    </button>
                  ) : null}

                  <button
                    onClick={() => handleClose(n.id)}
                    className="px-2.5 py-1 text-[11px] font-semibold bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-300 border border-emerald-500/30 rounded transition"
                  >
                    Close Note
                  </button>
                </>
              )}
            </div>

            {/* Response Input Sub-form */}
            {activeResponseId === n.id && (
              <div className="mt-3 pt-3 border-t border-slate-800 space-y-2">
                <input
                  type="text"
                  value={responseText}
                  onChange={(e) => setResponseText(e.target.value)}
                  placeholder="Type response to this review note..."
                  className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-xs text-slate-200"
                />
                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => setActiveResponseId(null)}
                    className="px-2 py-1 text-[10px] text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleRespond(n.id)}
                    className="px-3 py-1 text-xs font-semibold bg-indigo-600 text-white rounded hover:bg-indigo-500"
                  >
                    Submit Response
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
