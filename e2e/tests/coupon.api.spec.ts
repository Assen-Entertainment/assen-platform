import { test, expect, request } from '@playwright/test';
import * as fs from 'node:fs';

// seed_coupon.py writes tokens + coupon ids here. This gate proves the coupon
// lifecycle, the point ledger, the blocked-fan redeem refusal, and the gates.
const seedPath = process.env.COUPON_SEED_OUT;
if (!seedPath) {
  throw new Error('COUPON_SEED_OUT must point at the seed JSON written by seed_coupon.py');
}
const seed = JSON.parse(fs.readFileSync(seedPath, 'utf-8'));

const OP = '/api/operator/coupon';
const FAN = '/api/fan/coupon';

function bearer(token: string) {
  return { authorization: `Bearer ${token}` };
}

test('operator redeems an active coupon, minting a redemption id', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(`${OP}/coupons/${seed.activeCouponId}/redeem`, {
    headers: bearer(seed.operatorToken),
    data: {},
  });
  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(body.status).toBe('redeemed');
  expect(body.redemption_id).toBeTruthy();
});

test('a blocked fan coupon cannot be redeemed (400)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(`${OP}/coupons/${seed.blockedCouponId}/redeem`, {
    headers: bearer(seed.operatorToken),
    data: {},
  });
  expect(res.status()).toBe(400);
});

test('operator issues, cancels, and expires coupons', async () => {
  const ctx = await request.newContext();
  const op = bearer(seed.operatorToken);
  const issue = async () =>
    (await ctx.post(`${OP}/coupons`, { headers: op, data: { fan_id: seed.fanId, coupon_type: 'event' } })).json();

  const c1 = await issue();
  expect(c1.status).toBe('active');
  const cancelled = await ctx.post(`${OP}/coupons/${c1.id}/cancel`, { headers: op });
  expect(cancelled.status()).toBe(200);
  expect((await cancelled.json()).status).toBe('cancelled');

  const c2 = await issue();
  const expired = await ctx.post(`${OP}/coupons/${c2.id}/expire`, { headers: op });
  expect(expired.status()).toBe(200);
  expect((await expired.json()).status).toBe('expired');
});

test('operator grants and adjusts points; balance reflects the ledger', async () => {
  const ctx = await request.newContext();
  const op = bearer(seed.operatorToken);
  const grant = await ctx.post(`${OP}/points/grant`, {
    headers: op,
    data: { fan_id: seed.fanId, delta: 40, reason: 'welcome' },
  });
  expect(grant.status()).toBe(200);
  const adjust = await ctx.post(`${OP}/points/adjust`, {
    headers: op,
    data: { fan_id: seed.fanId, delta: -10 },
  });
  expect(adjust.status()).toBe(200);
  const bal = await ctx.get(`${OP}/points/${seed.fanId}`, { headers: op });
  expect((await bal.json()).balance).toBe(30);
});

test('a retried grant with the same reference is idempotent', async () => {
  const ctx = await request.newContext();
  const op = bearer(seed.operatorToken);
  const body = { fan_id: seed.fanId, delta: 15, reference: 'e2e-visit-1' };
  const first = await ctx.post(`${OP}/points/grant`, { headers: op, data: body });
  const again = await ctx.post(`${OP}/points/grant`, { headers: op, data: body });
  expect(first.status()).toBe(200);
  expect(again.status()).toBe(200);
  expect((await again.json()).id).toBe((await first.json()).id);
});

test('an adjustment that would underflow the balance is refused (400)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(`${OP}/points/adjust`, {
    headers: bearer(seed.operatorToken),
    data: { fan_id: seed.blockedFanId, delta: -5 },
  });
  expect(res.status()).toBe(400);
});

test('a fan reads their own coupons and point balance', async () => {
  const ctx = await request.newContext();
  const coupons = await ctx.get(`${FAN}/coupons`, { headers: bearer(seed.fanToken) });
  expect(coupons.status()).toBe(200);
  expect((await coupons.json()).length).toBeGreaterThanOrEqual(1);
  const points = await ctx.get(`${FAN}/points`, { headers: bearer(seed.fanToken) });
  expect(points.status()).toBe(200);
  expect(typeof (await points.json()).balance).toBe('number');
});

test('a staff token is refused on the fan surface, and the operator surface refuses fan/anon', async () => {
  const ctx = await request.newContext();
  expect((await ctx.get(`${FAN}/coupons`, { headers: bearer(seed.operatorToken) })).status()).toBe(403);
  expect([401, 403]).toContain((await ctx.get(`${OP}/coupons`, { headers: bearer(seed.fanToken) })).status());
  expect([401, 403]).toContain((await ctx.get(`${OP}/coupons`)).status());
});
