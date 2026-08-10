import { Outlet } from 'react-router-dom';

export function AuthLayout() {
  return (
    <div className="grid min-h-screen place-items-center bg-mist p-4">
      <main className="w-full max-w-sm rounded bg-white p-8 shadow-sm">
        <h1 className="mb-6 text-xl font-semibold text-navy">Real Estate Factory</h1>
        <Outlet />
      </main>
    </div>
  );
}
