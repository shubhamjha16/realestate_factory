import { api } from '@/global/apiClient';
import { DisbursementCheck, PortfolioRollup, RentRollSummary } from '../types';

export const portfolioService = {
  async fetchRollup(properties: Record<string, unknown>[]): Promise<PortfolioRollup> {
    return api.post<PortfolioRollup>('/portfolio/rollup', { properties });
  },

  async fetchRentRoll(leases: Record<string, unknown>[], asOfDate?: string): Promise<RentRollSummary> {
    return api.post<RentRollSummary>('/portfolio/rent-roll', { leases, as_of_date: asOfDate });
  },

  async verifyDisbursement(
    certifiedPct: number,
    requestedPct: number,
    priorPct: number = 0
  ): Promise<DisbursementCheck> {
    return api.post<DisbursementCheck>('/portfolio/disbursement/verify', {
      certified_stage_pct: certifiedPct,
      requested_tranche_pct: requestedPct,
      prior_disbursed_pct: priorPct,
    });
  },
};
