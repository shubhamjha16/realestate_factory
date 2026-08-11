import { api } from '@/global/apiClient';
import { DeliverableProvenance, DeliverableSummary } from '../types';

export const deliverableService = {
  async listDeliverables(mandateId?: string): Promise<DeliverableSummary[]> {
    const query = mandateId ? `?mandate_id=${encodeURIComponent(mandateId)}` : '';
    return api.get<DeliverableSummary[]>(`/deliverables${query}`);
  },

  async getDeliverable(id: string): Promise<DeliverableSummary> {
    return api.get<DeliverableSummary>(`/deliverables/${id}`);
  },

  async getProvenance(id: string): Promise<DeliverableProvenance> {
    return api.get<DeliverableProvenance>(`/deliverables/${id}/provenance`);
  },
};
