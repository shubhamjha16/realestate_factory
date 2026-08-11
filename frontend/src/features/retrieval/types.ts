export interface CorpusSearchResult {
  id: string;
  locality: string;
  city: string;
  topic: string;
  content: string;
}

export interface CorpusSearchResponse {
  results: CorpusSearchResult[];
  audit_logged: boolean;
  error: string | null;
}
