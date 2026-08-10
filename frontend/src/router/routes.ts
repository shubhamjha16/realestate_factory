import { ROUTES } from '@/shared/constants/routes';

/**
 * Route table. Screens are added feature by feature from S5; the paths are fixed
 * now so `shared/constants/routes.ts` stays the single source for links.
 */
export interface RouteMeta {
  path: string;
  label: string;
  sprint: string;
}

export const APP_ROUTES: readonly RouteMeta[] = [
  { path: ROUTES.dashboard, label: 'Dashboard', sprint: 'S16' },
  { path: ROUTES.clients, label: 'Clients', sprint: 'S5' },
  { path: ROUTES.mandates, label: 'Mandates', sprint: 'S5' },
  { path: ROUTES.properties, label: 'Properties', sprint: 'S5' },
  { path: ROUTES.rera, label: 'RERA', sprint: 'S14' },
  { path: ROUTES.deliverables, label: 'Deliverables', sprint: 'S12' },
  { path: ROUTES.usage, label: 'Usage', sprint: 'S18' },
];
