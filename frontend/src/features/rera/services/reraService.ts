import { api } from '@/global/apiClient';
import { ExpiringApproval, ReraObligation, StampDutyCalculation } from '../types';

export const reraService = {
  async fetchObligations(state: string, regDate: string, endDate: string): Promise<ReraObligation[]> {
    return api.post<ReraObligation[]>('/compliance/rera/obligations', {
      state,
      rera_reg_date: regDate,
      project_end_date: endDate,
    });
  },

  async calculateStampDuty(
    state: string,
    consideration: number,
    circleRate: number,
    area: number,
    docType: string = 'sale_deed',
    gender: string = 'male'
  ): Promise<StampDutyCalculation> {
    return api.post<StampDutyCalculation>('/compliance/stamp-duty', {
      state,
      document_type: docType,
      consideration,
      circle_rate: circleRate,
      area,
      gender,
    });
  },

  async checkExpiringApprovals(approvals: Record<string, unknown>[], withinDays: number = 90): Promise<ExpiringApproval[]> {
    return api.post<ExpiringApproval[]>('/compliance/approvals/expiring', {
      approvals,
      within_days: withinDays,
    });
  },
};
