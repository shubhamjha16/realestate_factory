/** Mirrors `backend/app/configs/jurisdictionConfig.py`. */

export interface Jurisdiction {
  code: string;
  name: string;
  reraAuthority: string;
  localAreaUnits: readonly string[];
}

export const JURISDICTIONS: readonly Jurisdiction[] = [
  { code: 'MH', name: 'Maharashtra', reraAuthority: 'MahaRERA', localAreaUnits: ['guntha', 'are'] },
  { code: 'KA', name: 'Karnataka', reraAuthority: 'K-RERA', localAreaUnits: ['guntha', 'cent'] },
  { code: 'UP', name: 'Uttar Pradesh', reraAuthority: 'UP RERA', localAreaUnits: ['bigha', 'biswa'] },
  { code: 'DL', name: 'Delhi', reraAuthority: 'Delhi RERA', localAreaUnits: ['bigha', 'biswa'] },
  { code: 'TN', name: 'Tamil Nadu', reraAuthority: 'TNRERA', localAreaUnits: ['cent', 'ground'] },
  { code: 'TG', name: 'Telangana', reraAuthority: 'TG RERA', localAreaUnits: ['guntha'] },
  { code: 'GJ', name: 'Gujarat', reraAuthority: 'GujRERA', localAreaUnits: ['vigha'] },
  { code: 'HR', name: 'Haryana', reraAuthority: 'HARERA', localAreaUnits: ['bigha', 'kanal', 'marla'] },
  { code: 'WB', name: 'West Bengal', reraAuthority: 'WBRERA', localAreaUnits: ['katha', 'bigha'] },
  { code: 'RJ', name: 'Rajasthan', reraAuthority: 'RERA Rajasthan', localAreaUnits: ['bigha', 'biswa'] },
] as const;

/** A bigha is not one area. It differs by state and by district — S6 resolves it. */
export const AMBIGUOUS_LOCAL_UNITS = ['bigha', 'biswa', 'katha', 'vigha'] as const;
