import { test, expect, request } from '@playwright/test';
import * as fs from 'node:fs';

// The seed (e2e/seed_kpi.py) writes tokens + window + expected KPIs here; the
// expected values are derived from the seeded events, independent of the code
// under test, so a regression in the aggregation fails this gate.
const seedPath = process.env.KPI_SEED_OUT;
if (!seedPath) {
  throw new Error('KPI_SEED_OUT must point at the seed JSON written by seed_kpi.py');
}
const seed = JSON.parse(fs.readFileSync(seedPath, 'utf-8'));

const metricsUrl = `/api/operator/metrics/?start=${seed.start}&end=${seed.end}`;

const ALL_KPI_FIELDS = [
  'period_start',
  'period_end',
  'msfc',
  'verified_visit_fans',
  'safe_fan_continuation_rate',
  'first_visit_fans',
  'thirty_day_return_rate',
  'favorite_registrations',
  'favorite_to_visit_rate',
  'schedule_view_fans',
  'schedule_to_reservation_rate',
  'schedule_to_visit_rate',
  'signups',
  'visitor_signup_rate',
  'favorite_registration_rate',
  'cheki_record_rate',
  'safety_reports_created',
  'safety_report_rate_per_visit',
  'users_blocked',
  'excluded_risk_fans',
];

test('operator metrics returns the seeded MSFC/guardrail KPIs', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(metricsUrl, {
    headers: { authorization: `Bearer ${seed.operatorToken}` },
  });
  expect(res.status()).toBe(200);
  const body = await res.json();

  expect(body.msfc).toBe(seed.expected.msfc);
  expect(body.verified_visit_fans).toBe(seed.expected.verified_visit_fans);
  expect(body.safe_fan_continuation_rate).toBe(seed.expected.safe_fan_continuation_rate);
  expect(body.safety_reports_created).toBe(seed.expected.safety_reports_created);
  expect(body.users_blocked).toBe(seed.expected.users_blocked);
  // The blocked fan is excluded from MSFC via the live safety-model join.
  expect(body.excluded_risk_fans).toBe(seed.expected.excluded_risk_fans);

  // Full contract: every documented KPI field is present.
  for (const field of ALL_KPI_FIELDS) {
    expect(body).toHaveProperty(field);
  }
  // Counts-only contract: no name/price/PII-shaped keys leak into the body.
  for (const key of Object.keys(body)) {
    expect(key).not.toMatch(/name|price|amount|narrative|phone|email/i);
  }
});

test('a fan token is refused (operator-gated)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(metricsUrl, {
    headers: { authorization: `Bearer ${seed.fanToken}` },
  });
  expect([401, 403]).toContain(res.status());
});

test('an unauthenticated request is refused', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(metricsUrl);
  expect([401, 403]).toContain(res.status());
});

test('an inverted window is rejected (422)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get('/api/operator/metrics/?start=2026-06-10&end=2026-06-01', {
    headers: { authorization: `Bearer ${seed.operatorToken}` },
  });
  expect(res.status()).toBe(422);
});

test('the v0 dashboard endpoint still serves (no regression)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get('/api/operator/dashboard/', {
    headers: { authorization: `Bearer ${seed.operatorToken}` },
  });
  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(body).toHaveProperty('business_day');
  expect(body).toHaveProperty('visits');
});
