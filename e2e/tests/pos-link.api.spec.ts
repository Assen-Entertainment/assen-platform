import { test, expect, request } from '@playwright/test';
import * as fs from 'node:fs';

// seed_pos.py writes tokens + the expected coverage (derived from seeded rows on
// an isolated date) here; a regression in the link/coverage surface fails this gate.
const seedPath = process.env.POS_SEED_OUT;
if (!seedPath) {
  throw new Error('POS_SEED_OUT must point at the seed JSON written by seed_pos.py');
}
const seed = JSON.parse(fs.readFileSync(seedPath, 'utf-8'));

const ORDERS = '/api/operator/pos/orders';
const COVERAGE = '/api/operator/pos/coverage';

test('operator reads the seeded POS link coverage (연결률)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(`${COVERAGE}?date=${seed.seedDate}`, {
    headers: { authorization: `Bearer ${seed.operatorToken}` },
  });
  expect(res.status()).toBe(200);
  const body = await res.json();

  expect(body.total_active_visits).toBe(seed.expected.total_active_visits);
  expect(body.linked_visits).toBe(seed.expected.linked_visits);
  expect(body.unlinked_visits).toBe(seed.expected.unlinked_visits);
  expect(body.link_rate).toBe(seed.expected.link_rate);
  // The seeded unlinked visit appears in the 미연결 목록.
  const unlinkedIds = body.unlinked.map((u: { visit_id: string }) => u.visit_id);
  expect(unlinkedIds).toContain(seed.unlinkedVisitId);
  // No fan PII leaks into the operator coverage body.
  const blob = JSON.stringify(body);
  expect(blob).not.toMatch(/phone|email|narrative/i);
});

test('a duplicate active receipt is rejected (400)', async () => {
  const ctx = await request.newContext();
  // Re-using the seeded receipt for the unlinked visit must be refused; the POST
  // is rejected so it mutates nothing (safe under parallel runs).
  const res = await ctx.post(ORDERS, {
    headers: { authorization: `Bearer ${seed.operatorToken}` },
    data: { visit_id: seed.unlinkedVisitId, pos_receipt_no: seed.linkedReceipt },
  });
  expect(res.status()).toBe(400);
});

test('operator links a fresh visit end to end', async () => {
  const ctx = await request.newContext();
  const auth = { authorization: `Bearer ${seed.operatorToken}` };
  // Create a fresh visit (own data, so this test is order-independent), then link
  // it — proving the wired create surface, not just the seed service path.
  const visitRes = await ctx.post('/api/operator/visits/', {
    headers: auth,
    data: { fan_id: seed.fanId },
  });
  expect(visitRes.status()).toBe(201);
  const visitId = (await visitRes.json()).id;

  const linkRes = await ctx.post(ORDERS, {
    headers: auth,
    data: {
      visit_id: visitId,
      pos_receipt_no: `POS-E2E-${Date.now()}`,
      payment_status: 'paid',
      payment_method: 'card',
      amount: 9000,
    },
  });
  expect(linkRes.status()).toBe(201);
  const link = await linkRes.json();
  expect(link.payment_status).toBe('paid');
  expect(link.link_method).toBe('manual');
});

test('a fan token is refused (operator-gated)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(`${COVERAGE}?date=${seed.seedDate}`, {
    headers: { authorization: `Bearer ${seed.fanToken}` },
  });
  expect([401, 403]).toContain(res.status());
});

test('an unauthenticated request is refused', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(ORDERS);
  expect([401, 403]).toContain(res.status());
});
