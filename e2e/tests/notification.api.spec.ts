import { test, expect, request } from '@playwright/test';
import * as fs from 'node:fs';

// seed_notification.py writes operator + fan tokens here; this gate proves the
// live notification policy guard: the allowed 4 dispatch, every forbidden path is
// refused (422), and the operator surface rejects non-operators.
const seedPath = process.env.NOTIFICATION_SEED_OUT;
if (!seedPath) {
  throw new Error('NOTIFICATION_SEED_OUT must point at the seed JSON written by seed_notification.py');
}
const seed = JSON.parse(fs.readFileSync(seedPath, 'utf-8'));

const POLICY = '/api/operator/notifications/policy';
const DISPATCH = '/api/operator/notifications/dispatch';

function bearer(token: string) {
  return { authorization: `Bearer ${token}` };
}

function futureDate(days: number): string {
  return new Date(Date.now() + days * 864e5).toISOString().slice(0, 10);
}

const baseDispatch = {
  category: 'reservation_status',
  token: 'device-1',
  title: '예약 확정',
  body: '예약이 확정되었습니다.',
};

test('the policy registry lists the allowed four and the forbidden kinds', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(POLICY, { headers: bearer(seed.operatorToken) });
  expect(res.status()).toBe(200);
  const body = await res.json();
  const allowed = body.allowed.map((c: { value: string }) => c.value).sort();
  expect(allowed).toEqual(['coupon', 'event_notice', 'favorite_cast_schedule', 'reservation_status']);
  const forbidden = body.forbidden.map((f: { value: string }) => f.value);
  expect(forbidden).toContain('high_value_payment_inducement');
});

test('an allowed category dispatches and is accepted', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(DISPATCH, { headers: bearer(seed.operatorToken), data: baseDispatch });
  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(body.accepted).toBe(true);
  expect(body.category).toBe('reservation_status');
  expect(body.message_id).toBeTruthy();
});

test('a forbidden category is refused (422)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(DISPATCH, {
    headers: bearer(seed.operatorToken),
    data: { ...baseDispatch, category: 'high_value_payment_inducement' },
  });
  expect(res.status()).toBe(422);
});

test('an unknown category is refused fail-closed (422)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(DISPATCH, {
    headers: bearer(seed.operatorToken),
    data: { ...baseDispatch, category: 'surprise_promo' },
  });
  expect(res.status()).toBe(422);
});

test('a real-time presence field is refused for any category (422)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(DISPATCH, {
    headers: bearer(seed.operatorToken),
    data: { ...baseDispatch, category: 'event_notice', data: { in_store_now: 'true' } },
  });
  expect(res.status()).toBe(422);
});

test('a cased real-time presence key cannot slip past the guard (422)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(DISPATCH, {
    headers: bearer(seed.operatorToken),
    data: { ...baseDispatch, category: 'event_notice', data: { In_Store_Now: 'true' } },
  });
  expect(res.status()).toBe(422);
});

test('a caller cannot override the stamped scheduled_date via data (422)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(DISPATCH, {
    headers: bearer(seed.operatorToken),
    data: {
      ...baseDispatch,
      category: 'favorite_cast_schedule',
      scheduled_date: futureDate(4),
      data: { scheduled_date: '2020-01-01' },
    },
  });
  expect(res.status()).toBe(422);
});

test('a favourite-cast schedule must reference a future date', async () => {
  const ctx = await request.newContext();
  const op = bearer(seed.operatorToken);

  const ok = await ctx.post(DISPATCH, {
    headers: op,
    data: { ...baseDispatch, category: 'favorite_cast_schedule', scheduled_date: futureDate(4) },
  });
  expect(ok.status()).toBe(200);

  const missing = await ctx.post(DISPATCH, {
    headers: op,
    data: { ...baseDispatch, category: 'favorite_cast_schedule' },
  });
  expect(missing.status()).toBe(422);

  const past = await ctx.post(DISPATCH, {
    headers: op,
    data: { ...baseDispatch, category: 'favorite_cast_schedule', scheduled_date: futureDate(-1) },
  });
  expect(past.status()).toBe(422);
});

test('the operator surface refuses fan and anonymous callers', async () => {
  const ctx = await request.newContext();
  expect([401, 403]).toContain((await ctx.get(POLICY, { headers: bearer(seed.fanToken) })).status());
  expect([401, 403]).toContain((await ctx.get(POLICY)).status());
  const fanDispatch = await ctx.post(DISPATCH, { headers: bearer(seed.fanToken), data: baseDispatch });
  expect([401, 403]).toContain(fanDispatch.status());
});
