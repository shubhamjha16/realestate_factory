export interface WebhookDeliveryResult {
  target_url: string;
  event_type: string;
  status: 'delivered' | 'dead_letter';
  timestamp: number;
  signature: string;
  attempts: {
    attempt: number;
    status: string;
    http_code: number;
    backoff_seconds: number;
    timestamp: number;
  }[];
}

export interface WebhookVerifyResult {
  valid: boolean;
  message: string;
}

export interface JobProgressEvent {
  job_id: string;
  step: number;
  total_steps: number;
  stage: string;
  message: string;
}
