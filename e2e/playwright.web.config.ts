import { defineConfig } from '@playwright/test';

// Web/UI E2E against the composed local web shell (scripts/build-web-local.sh ->
// serve-web-local.sh, default http://127.0.0.1:8080). Kept separate from the
// API config so the documented `npx playwright test` API flow does not try to
// reach the web shell. Run as a Claude QA gate; intentionally not wired into CI.
//
//   WEB_BASE_URL=http://127.0.0.1:8080 npm run test:web
//
// Deployed-dev runs (WEB_BASE_URL=https://dev.assenent.com): dev.assenent.com occasionally
// resolves to a stale Cafe24 IP (DNS flap). Set DEV_ALB_IP to the current ALB IP to pin the
// browser's resolution to the real ALB via --host-resolver-rules (TLS SNI stays the hostname,
// so the ACM cert still matches):
//   DEV_ALB_IP=$(python -c "import socket;print(socket.gethostbyname('<alb-dns>'))") \
//   WEB_BASE_URL=https://dev.assenent.com \
//   node_modules/.bin/playwright test tests/dev-fan-journey.web.spec.ts \
//     --config playwright.web.config.ts --project=chromium
const devAlbIp = process.env.DEV_ALB_IP;
const baseHost = new URL(process.env.WEB_BASE_URL ?? 'https://dev.assenent.com').hostname;

export default defineConfig({
  testDir: './tests',
  testMatch: ['**/*.web.spec.ts'],
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    trace: 'on',
    ...(devAlbIp
      ? { launchOptions: { args: [`--host-resolver-rules=MAP ${baseHost} ${devAlbIp}`] } }
      : {}),
  },
  // A named project so `--project=chromium` resolves; it inherits the top-level `use`.
  projects: [{ name: 'chromium' }],
});
