import { defineConfig } from '@playwright/test';

// API-level E2E against a live local Assen API (default http://127.0.0.1:8000).
// Run as a Claude QA gate (see e2e/README.md); intentionally not wired into CI.
export default defineConfig({
  testDir: './tests',
  // Default suite is the API-level specs only. The web/UI specs (*.web.spec.ts)
  // need the composed Flutter web shell (scripts/serve-web-local.sh), not the
  // API server, so they run via playwright.web.config.ts instead — keeping the
  // documented `npx playwright test` API flow self-contained.
  testMatch: ['**/*.api.spec.ts'],
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8000',
    trace: 'on',
  },
});
