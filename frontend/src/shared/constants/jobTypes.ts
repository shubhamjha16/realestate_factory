/**
 * Mirrors `backend/app/configs/jobTypes.py`.
 *
 * Hand-mirrored at S1; from S3 this file is checked against the generated
 * `packages/api-types` in CI, so drift is a build failure rather than a 422 the
 * user discovers.
 */

export const VALUATION_TYPES = [
  'valuation_report',
  'due_diligence_report',
  'construction_disbursement_report',
] as const;

export const COMPLIANCE_TYPES = [
  'rera_registration',
  'rera_quarterly_report',
  'fema_compliance',
  'environment_impact_assessment',
  'noc_application',
] as const;

export const AGREEMENT_TYPES = [
  'sale_deed',
  'lease_agreement',
  'rental_agreement',
  'development_agreement',
  'mou',
  'power_of_attorney',
] as const;

export const RECONCILIATION_TYPES = ['rent_roll_report', 'portfolio_report'] as const;

export const ALL_JOB_TYPES = [
  ...VALUATION_TYPES,
  ...COMPLIANCE_TYPES,
  ...AGREEMENT_TYPES,
  ...RECONCILIATION_TYPES,
] as const;

export type JobType = (typeof ALL_JOB_TYPES)[number];
export type GraphPath = 'valuation' | 'compliance' | 'agreement' | 'reconciliation';

export const PATH_BY_JOB_TYPE: Record<JobType, GraphPath> = {
  ...Object.fromEntries(VALUATION_TYPES.map((t) => [t, 'valuation'])),
  ...Object.fromEntries(COMPLIANCE_TYPES.map((t) => [t, 'compliance'])),
  ...Object.fromEntries(AGREEMENT_TYPES.map((t) => [t, 'agreement'])),
  ...Object.fromEntries(RECONCILIATION_TYPES.map((t) => [t, 'reconciliation'])),
} as Record<JobType, GraphPath>;

export const JOB_TYPE_LABELS: Record<JobType, string> = {
  valuation_report: 'Valuation report',
  due_diligence_report: 'Due diligence report',
  construction_disbursement_report: 'Construction disbursement report',
  rera_registration: 'RERA registration',
  rera_quarterly_report: 'RERA quarterly report',
  fema_compliance: 'FEMA compliance',
  environment_impact_assessment: 'Environment impact assessment',
  noc_application: 'NOC application',
  sale_deed: 'Sale deed',
  lease_agreement: 'Lease agreement',
  rental_agreement: 'Rental agreement',
  development_agreement: 'Development agreement',
  mou: 'Memorandum of understanding',
  power_of_attorney: 'Power of attorney',
  rent_roll_report: 'Rent roll report',
  portfolio_report: 'Portfolio report',
};
