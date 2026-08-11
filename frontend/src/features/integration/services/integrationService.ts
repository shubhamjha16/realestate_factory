import { api } from '@/global/apiClient';
import { WebhookDeliveryResult, WebhookVerifyResult } from '../types';

export const integrationService = {
  async deliverWebhook(
    url: string,
    secret: string,
    payload: Record<string, unknown>,
    simulateFailures: number = 0
  ): Promise<WebhookDeliveryResult> {
    return api.post<WebhookDeliveryResult>('/webhooks/deliver', {
      url,
      secret,
      event_type: 'valuation.completed',
      payload,
      simulate_failures: simulateFailures,
    });
  },

  async verifyWebhook(secret: string, timestamp: number, rawBody: string, signature: string): Promise<WebhookVerifyResult> {
    return api.post<WebhookVerifyResult>('/webhooks/verify', {
      secret,
      timestamp,
      raw_body: rawBody,
      signature,
    });
  },
};
