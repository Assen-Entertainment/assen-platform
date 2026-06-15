import { defineConfig } from '@playwright/test';

// API-level E2E against a live local Assen API (default http://127.0.0.1:8000).
// Run as a Claude QA gate (see e2e/README.md); intentionally not wired into CI.
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8000',
    trace: 'on',
  },
});
