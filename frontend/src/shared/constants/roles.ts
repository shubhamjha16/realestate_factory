export const ROLES = ['partner', 'valuer', 'analyst', 'readonly', 'client'] as const;
export type Role = (typeof ROLES)[number];

export const ROLE_LABELS: Record<Role, string> = {
  partner: 'Partner',
  valuer: 'Registered valuer',
  analyst: 'Analyst',
  readonly: 'Read only',
  client: 'Client',
};

/**
 * Client-side gating is presentation only. Every one of these is enforced at the
 * repository layer on the backend (S5, S13); the console hides what the engine
 * would refuse, it does not decide it.
 */
export const CAN_SIGN: readonly Role[] = ['partner', 'valuer'];
export const CAN_REVIEW: readonly Role[] = ['partner', 'valuer'];
export const CAN_EDIT: readonly Role[] = ['partner', 'valuer', 'analyst'];
