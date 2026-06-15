import { test, expect, request } from '@playwright/test';
import * as fs from 'node:fs';

// seed_handling.py writes tokens + expected aggregates here; the expected values
// are derived from the seeded rows, independent of the code under test, so a
// regression in the aggregation fails this gate.
const seedPath = process.env.HANDLING_SEED_OUT;
if (!seedPath) {
  throw new Error('HANDLING_SEED_OUT must point at the seed JSON written by seed_handling.py');
}
const seed = JSON.parse(fs.readFileSync(seedPath, 'utf-8'));

const url = '/api/safety/handling-stats';

const FIELDS = [
  'window_days',
  'as_of',
  'open_total',
  'open_received',
  'open_reviewing',
  'open_actioned',
  'open_low',
  'open_medium',
  'open_high',
  'open_critical',
  'oldest_open_age_seconds',
  'resolved_in_window',
  'median_handling_seconds',
  'avg_handling_seconds',
];

test('operator gets the seeded report-handling stats', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(url, {
    headers: { authorization: `Bearer ${seed.operatorToken}` },
  });
  expect(res.status()).toBe(200);
  const body = await res.json();

  expect(body.open_total).toBe(seed.expected.open_total);
  expect(body.open_received).toBe(seed.expected.open_received);
  expect(body.open_reviewing).toBe(seed.expected.open_reviewing);
  expect(body.open_actioned).toBe(seed.expected.open_actioned);
  expect(body.open_low).toBe(seed.expected.open_low);
  expect(body.open_medium).toBe(seed.expected.open_medium);
  expect(body.open_high).toBe(seed.expected.open_high);
  expect(body.open_critical).toBe(seed.expected.open_critical);
  expect(body.resolved_in_window).toBe(seed.expected.resolved_in_window);

  // Durations are non-negative seconds (the resolved report was closed ~instantly).
  expect(body.oldest_open_age_seconds).toBeGreaterThanOrEqual(0);
  expect(body.median_handling_seconds).toBeGreaterThanOrEqual(0);
  expect(body.avg_handling_seconds).toBeGreaterThanOrEqual(0);

  // Full contract: every documented field is present.
  for (const field of FIELDS) {
    expect(body).toHaveProperty(field);
  }
  // Counts-only contract: no name/price/PII-shaped keys leak into the body.
  for (const key of Object.keys(body)) {
    expect(key).not.toMatch(/name|price|amount|narrative|phone|email/i);
  }
});

test('a fan token is refused (operator-gated)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(url, {
    headers: { authorization: `Bearer ${seed.fanToken}` },
  });
  expect([401, 403]).toContain(res.status());
});

test('an unauthenticated request is refused', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(url);
  expect([401, 403]).toContain(res.status());
});

test('an out-of-range window is rejected (422)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(`${url}?window_days=0`, {
    headers: { authorization: `Bearer ${seed.operatorToken}` },
  });
  expect(res.status()).toBe(422);
});
