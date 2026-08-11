import { api } from '@/global/apiClient';
import { CorpusSearchResponse } from '../types';

export const retrievalService = {
  async searchCorpus(targetFirmId: string, locality: string = '', topic: string = 'market_analysis'): Promise<CorpusSearchResponse> {
    return api.post<CorpusSearchResponse>('/retrieval/search', {
      target_firm_id: targetFirmId,
      locality,
      topic,
    });
  },
};
