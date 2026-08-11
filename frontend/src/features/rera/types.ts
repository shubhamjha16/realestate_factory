export interface ReraObligation {
  period: string;
  period_start: string;
  period_end: string;
  due_date: string;
  authority: string;
  status: 'pending' | 'completed';
  filing_type: string;
}

export interface StampDutyCalculation {
  state: string;
  document_type: string;
  agreed_consideration: string;
  circle_rate_per_unit: string;
  area: string;
  circle_valuation: string;
  taxable_value: string;
  applied_basis: 'agreed_consideration' | 'circle_rate_floor';
  stamp_duty_rate: string;
  stamp_duty_amount: string;
  registration_fee_amount: string;
  total_statutory_dues: string;
}

export interface ExpiringApproval {
  kind: string;
  issuing_authority: string;
  valid_until: string;
  days_remaining: number;
  is_expired: boolean;
  is_expiring_soon: boolean;
  status_warning: string;
}
