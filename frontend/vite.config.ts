import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  // The built screen uses B12's same-origin /ws. For Vite development, set
  // AEGIS_GROUND_URL to the ground server's configured HTTP origin.
  server: process.env.AEGIS_GROUND_URL
    ? { proxy: { '/ws': { target: process.env.AEGIS_GROUND_URL, ws: true } } }
    : undefined,
  test: { environment: 'jsdom', include: ['src/**/*.test.{ts,tsx}'] },
});
