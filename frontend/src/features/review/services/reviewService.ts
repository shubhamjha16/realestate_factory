import { api } from '@/global/apiClient';
import { CreateNotePayload, ReviewNote, SignoffResponse } from '../types';

export const reviewService = {
  async listNotes(deliverableId: string): Promise<ReviewNote[]> {
    return api.get<ReviewNote[]>(`/deliverables/${deliverableId}/notes`);
  },

  async createNote(deliverableId: string, payload: CreateNotePayload): Promise<ReviewNote> {
    return api.post<ReviewNote>(`/deliverables/${deliverableId}/notes`, { ...payload });
  },

  async respondNote(noteId: string, responseText: string): Promise<ReviewNote> {
    return api.post<ReviewNote>(`/notes/${noteId}/respond`, { response: responseText });
  },

  async closeNote(noteId: string): Promise<ReviewNote> {
    return api.post<ReviewNote>(`/notes/${noteId}/close`, {});
  },

  async signDeliverable(deliverableId: string, assetClass: string = 'land_and_building'): Promise<SignoffResponse> {
    return api.post<SignoffResponse>(`/deliverables/${deliverableId}/sign`, { asset_class: assetClass });
  },
};
