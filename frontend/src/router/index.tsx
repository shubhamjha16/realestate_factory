import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { AppLayout, AuthLayout } from '@/layouts';
import { EmptyState } from '@/components/feedback';
import { ROUTES } from '@/shared/constants/routes';
import { APP_ROUTES } from './routes';

/**
 * Every screen is `lazy()`-loaded per route from S5, so the map library never
 * reaches a user who is looking at a rent roll.
 */
const router = createBrowserRouter([
  {
    element: <AuthLayout />,
    children: [
      {
        path: ROUTES.signin,
        element: <EmptyState title="Sign in" description="Auth lands in S5." />,
      },
    ],
  },
  {
    element: <AppLayout />,
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
