import { test, expect, type APIRequestContext } from '@playwright/test';
import { createHmac } from 'node:crypto';
import { readFileSync } from 'node:fs';

// Every test signs up a fan (a DB write); serialise this file so the throwaway
// sqlite harness DB is not hit by concurrent signup writers ("database is locked"
// under fullyParallel). The production DB is postgres, where this is a non-issue.
test.describe.configure({ mode: 'serial' });

// Reproduces config.otp.MockOtpSender.code_for (HMAC-SHA256 under the dev secret,
// first 8 hex digits mod 1e6) so the E2E can sign up a fan — and thus obtain a
// real token — without any SMS. Same derivation as the fan-signup spec.
function codeFor(phone: string): string {
  const digest = createHmac('sha256', 'assen-dev-otp').update(phone, 'utf8').digest('hex');
  return String(parseInt(digest.slice(0, 8), 16) % 1_000_000).padStart(6, '0');
}

// Sign up a fresh fan and return its access token (app/body delivery).
async function signupFan(
  request: APIRequestContext,
  phone: string,
  nickname: string,
): Promise<string> {
  await request.post('/api/fan/signup/otp', { data: { phone } });
  const signup = await request.post('/api/fan/signup', {
    data: { phone, otp_code: codeFor(phone), nickname, consent_terms: true, consent_privacy: true, age_over_14: true },
  });
  expect(signup.status()).toBe(200);
  const token = (await signup.json()).access_token as string;
  expect(token).toBeTruthy();
  return token;
}

// The KPI seed (e2e/seed_kpi.py) writes an operator token; reused here to verify
// the operator side. Absent → the cross-surface test skips (core tests still run).
function operatorToken(): string | null {
  try {
    const seed = JSON.parse(readFileSync(process.env.KPI_SEED_OUT ?? '.seed.json', 'utf8'));
    return (seed.operatorToken as string) ?? null;
  } catch {
    return null;
  }
}

const SECRET = '그 손님이 사적 연락처를 계속 요구했어요 010-1234-5678';

test('a fan files a safety report and gets a receipt only', async ({ request }) => {
  const token = await signupFan(request, '+821050001001', '신고팬');
  const res = await request.post('/api/safety/fan-reports', {
    headers: { authorization: `Bearer ${token}` },
    data: { report_type: 'private_contact', narrative: SECRET },
  });
  expect(res.status()).toBe(201);
  const body = await res.json();
  expect(body.safety_report_id).toBeTruthy();
  expect(body.status).toBe('received');
  // Receipt only — no severity/visibility/narrative echoed back to the fan.
  expect(Object.keys(body).sort()).toEqual(['created_at', 'safety_report_id', 'status']);
  expect(JSON.stringify(body)).not.toContain('010-1234-5678');
});

test('a non-fan-reportable type is rejected (422)', async ({ request }) => {
  const token = await signupFan(request, '+821050001002', '신고팬2');
  const res = await request.post('/api/safety/fan-reports', {
    headers: { authorization: `Bearer ${token}` },
    data: { report_type: 'refund_dispute', narrative: 'x' },
  });
  expect(res.status()).toBe(422);
});

test('an unknown report_type is rejected (422)', async ({ request }) => {
  const token = await signupFan(request, '+821050001003', '신고팬3');
  const res = await request.post('/api/safety/fan-reports', {
    headers: { authorization: `Bearer ${token}` },
    data: { report_type: 'bogus' },
  });
  expect(res.status()).toBe(422);
});

test('filing a report requires authentication', async ({ request }) => {
  const res = await request.post('/api/safety/fan-reports', {
    data: { report_type: 'verbal_abuse' },
  });
  expect([401, 403]).toContain(res.status());
});

test('a fan-filed report reaches operators with the narrative withheld', async ({ request }) => {
  const opToken = operatorToken();
  test.skip(!opToken, 'no seeded operator token (.seed.json) — run seed_kpi.py first');
  const token = await signupFan(request, '+821050001004', '신고팬4');
  const filed = await request.post('/api/safety/fan-reports', {
    headers: { authorization: `Bearer ${token}` },
    data: { report_type: 'unwanted_request', narrative: SECRET },
  });
  expect(filed.status()).toBe(201);
  const reportId = (await filed.json()).safety_report_id as string;

  const listed = await request.get('/api/safety/reports', {
    headers: { authorization: `Bearer ${opToken}` },
  });
  expect(listed.status()).toBe(200);
  const rows = (await listed.json()) as Array<Record<string, string>>;
  expect(rows.find((r) => r.safety_report_id === reportId)).toBeTruthy();
  // The reporter's narrative must never appear in the operator response.
  expect(await listed.text()).not.toContain('010-1234-5678');
});

test('a staff token cannot file a fan self-report (403)', async ({ request }) => {
  const opToken = operatorToken();
  test.skip(!opToken, 'no seeded operator token (.seed.json) — run seed_kpi.py first');
  // fan_auth is role-agnostic; the endpoint must reject a staff token so operator
  // traffic is never misclassified as a fan self-report.
  const res = await request.post('/api/safety/fan-reports', {
    headers: { authorization: `Bearer ${opToken}` },
    data: { report_type: 'verbal_abuse', narrative: 'x' },
  });
  expect(res.status()).toBe(403);
});
