import { test, expect } from '@playwright/test';
import { createHmac } from 'node:crypto';

// Reproduces config.otp.MockOtpSender.code_for (HMAC-SHA256 under the dev secret,
// first 8 hex digits mod 1e6) so the E2E can present a valid OTP without any SMS.
function codeFor(phone: string): string {
  const digest = createHmac('sha256', 'assen-dev-otp').update(phone, 'utf8').digest('hex');
  return String(parseInt(digest.slice(0, 8), 16) % 1_000_000).padStart(6, '0');
}

const PHONE = '+821099887766';

test('phone-OTP signup issues a token and serves the membership card', async ({ request }) => {
  const otp = await request.post('/api/fan/signup/otp', { data: { phone: PHONE } });
  expect(otp.status()).toBe(200);

  const signup = await request.post('/api/fan/signup', {
    data: {
      phone: PHONE,
      otp_code: codeFor(PHONE),
      nickname: '미오팬',
      consent_terms: true,
      consent_privacy: true,
    },
  });
  expect(signup.status()).toBe(200);
  const token = (await signup.json()).access_token as string;
  expect(token).toBeTruthy();

  const card = await request.get('/api/fan/membership-card', {
    headers: { authorization: `Bearer ${token}` },
  });
  expect(card.status()).toBe(200);
  const body = await card.json();
  expect(body.nickname).toBe('미오팬');
  expect(body.visit_count).toBe(0);
  // Counts-only / minimal PII: no phone/email/address leaks into the card.
  for (const key of Object.keys(body)) {
    expect(key).not.toMatch(/phone|email|address|password/i);
  }
});

test('signup without privacy consent is rejected (422)', async ({ request }) => {
  const res = await request.post('/api/fan/signup', {
    data: {
      phone: '+821000000000',
      otp_code: codeFor('+821000000000'),
      nickname: 'x',
      consent_terms: true,
      consent_privacy: false,
    },
  });
  expect(res.status()).toBe(422);
});

test('signup with a wrong OTP is rejected (422)', async ({ request }) => {
  const res = await request.post('/api/fan/signup', {
    data: {
      phone: '+821011112222',
      otp_code: '000000',
      nickname: 'x',
      consent_terms: true,
      consent_privacy: true,
    },
  });
  expect(res.status()).toBe(422);
});

test('membership card requires authentication', async ({ request }) => {
  const res = await request.get('/api/fan/membership-card');
  expect([401, 403]).toContain(res.status());
});

test('web signup delivers httpOnly cookies and authenticates the card via cookie', async ({ request }) => {
  const phone = '+821055667788';
  const signup = await request.post('/api/fan/signup', {
    data: {
      phone,
      otp_code: codeFor(phone),
      nickname: '웹팬',
      consent_terms: true,
      consent_privacy: true,
      web: true,
    },
  });
  expect(signup.status()).toBe(200);
  const body = await signup.json();
  expect(body.token_delivery).toBe('cookie');
  expect(body.access_token).toBe(''); // no secret in the JS-readable body
  const setCookie = (signup.headers()['set-cookie'] ?? '').toLowerCase();
  expect(setCookie).toContain('httponly');
  // The request context now holds the access cookie; the card authenticates with
  // no bearer header (web surface, ADR-0002).
  const card = await request.get('/api/fan/membership-card');
  expect(card.status()).toBe(200);
  expect((await card.json()).nickname).toBe('웹팬');
});
