import { defineConfig } from '@playwright/test';

// Web/UI E2E against the deployed dev over https (https://dev.assenent.com). Same shape as
// playwright.web.config.ts, plus one tolerance: while the dev subdomain's old Cafe24 A
// record ages out, a local resolver can oscillate between the ALB and the stale IP,
// causing intermittent TLS failures. If DEV_ALB_IP is set, chromium pins dev.assenent.com
// to that IP — the SNI/Host stay dev.assenent.com, so the ACM cert still validates. Unset
// => normal DNS (no-op), so this is safe anywhere. Run as a Claude QA gate; not in CI.
//
//   DEV_ALB_IP=$(dig +short assen-dev-api-...elb.amazonaws.com | head -1) \
//   WEB_BASE_URL=https://dev.assenent.com \
//   npx playwright test tests/<spec>.web.spec.ts --config playwright.devhttps.config.ts
const albIp = process.env.DEV_ALB_IP;

export default defineConfig({
  testDir: './tests',
  testMatch: ['**/*.web.spec.ts'],
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  reporter: [['list']],
  use: {
    trace: 'on',
    ignoreHTTPSErrors: false, // validate the real ACM cert
    launchOptions: albIp
      ? { args: [`--host-resolver-rules=MAP dev.assenent.com ${albIp}`] }
      : {},
  },
});
