export interface PortfolioRollup {
  total_properties: number;
  total_asset_value: string;
  total_built_up_area_sqft: string;
  concentration_by_city: { name: string; value: string; share_percentage: string }[];
  concentration_by_asset_class: { name: string; value: string; share_percentage: string }[];
  concentration_by_tenant: { name: string; value: string; share_percentage: string }[];
}

export interface RentRollSummary {
  as_of_date: string;
  total_active_leases: number;
  total_leased_area_sqft: string;
  total_monthly_rent: string;
  total_annual_rent: string;
  wault_years: string;
  expiry_profile: Record<string, { count: number; annual_rent: string }>;
}

export interface DisbursementCheck {
  approved: boolean;
  status_code: string;
  certified_stage_pct: string;
  prior_disbursed_pct: string;
  requested_tranche_pct: string;
  cumulative_requested_pct: string;
  message: string;
}
