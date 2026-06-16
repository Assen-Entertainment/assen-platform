import { defineConfig } from '@playwright/test';

// Web/UI E2E against the composed local web shell (scripts/build-web-local.sh ->
// serve-web-local.sh, default http://127.0.0.1:8080). Kept separate from the
// API config so the documented `npx playwright test` API flow does not try to
// reach the web shell. Run as a Claude QA gate; intentionally not wired into CI.
//
//   WEB_BASE_URL=http://127.0.0.1:8080 npm run test:web
export default defineConfig({
  testDir: './tests',
  testMatch: ['**/*.web.spec.ts'],
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    trace: 'on',
  },
});
