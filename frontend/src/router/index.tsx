import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { AppLayout, AuthLayout } from '@/layouts';
import { EmptyState } from '@/components/feedback';
import { SignInPage } from '@/features/auth';
import { ROUTES } from '@/shared/constants/routes';
import { RequireAuth } from './guards';
import { APP_ROUTES } from './routes';

/**
 * Every screen is `lazy()`-loaded per route from S6, so the map library never
 * reaches a user who is looking at a rent roll.
 *
 * `RequireAuth` is presentation. The engine refuses an unauthenticated request
 * with a 401 whatever the console does, and refuses a cross-firm one with a 404
 * — a guard here only saves a round trip.
 */
const router = createBrowserRouter([
  {
    element: <AuthLayout />,
    children: [{ path: ROUTES.signin, element: <SignInPage /> }],
  },
  {
    element: (
      <RequireAuth>
        <AppLayout />
      </RequireAuth>
    ),
    children: APP_ROUTES.map((route) => ({
      path: route.path,
      element: (
        <EmptyState title={route.label} description={`This screen lands in ${route.sprint}.`} />
      ),
    })),
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
