export interface ReviewNote {
  id: string;
  deliverable_id: string;
  section_id: string | null;
  comparable_id: string | null;
  author_id: string | null;
  assigned_to: string | null;
  status: 'open' | 'responded' | 'closed';
  note: string;
  response: string | null;
  created_at: string | null;
}

export interface CreateNotePayload {
  note: string;
  section_id?: string;
  comparable_id?: string;
  assigned_to?: string;
}

export interface SignoffResponse {
  id: string;
  status: string;
  signed_by: string;
  signed_at: string;
}
