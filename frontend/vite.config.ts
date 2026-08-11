import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    strictPort: true,
  },
  build: {
    // S21 splits per route and commits a visualizer report. The map library is
    // the heavy one and is lazy-loaded inside features/comparables/ only.
    sourcemap: true,
  },
  test: {
    environment: 'jsdom',
    // The console fails loudly on a missing base URL, exactly as the engine does
    // on a missing required setting. Tests get a configured one rather than an
    // exemption from the rule.
    env: { VITE_API_BASE_URL: 'http://localhost:8004/api/v1' },
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.test.{ts,tsx}', 'src/**/*.test.{ts,tsx}'],
  },
});
