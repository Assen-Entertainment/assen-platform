import { test, expect, request } from '@playwright/test';
import * as fs from 'node:fs';

// seed_reservation.py writes tokens + the seeded future date here; a regression in
// the reservation/waitlist surface (routing, auth, block enforcement) fails this gate.
const seedPath = process.env.RESERVATION_SEED_OUT;
if (!seedPath) {
  throw new Error('RESERVATION_SEED_OUT must point at the seed JSON written by seed_reservation.py');
}
const seed = JSON.parse(fs.readFileSync(seedPath, 'utf-8'));

const OP = '/api/operator/reservations';
const FAN = '/api/fan/reservations';

// Distinct future dates per mutating test so parallel runs never collide on the
// (fan, date, time, type) active-slot uniqueness.
function isoPlus(base: string, days: number): string {
  const d = new Date(`${base}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

test('operator reads the seeded daily reservation list', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(`${OP}?date=${seed.seedDate}`, {
    headers: { authorization: `Bearer ${seed.operatorToken}` },
  });
  expect(res.status()).toBe(200);
  const rows = await res.json();
  expect(rows.length).toBeGreaterThanOrEqual(seed.expected.total);
  const statuses = rows.map((r: { status: string }) => r.status);
  expect(statuses).toContain('requested');
  expect(statuses).toContain('confirmed');
  // No fan PII leaks into the operator list body.
  expect(JSON.stringify(rows)).not.toMatch(/phone|email|narrative/i);
});

test('a fan registers and lists their own reservation', async () => {
  const ctx = await request.newContext();
  const auth = { authorization: `Bearer ${seed.fanToken}` };
  const created = await ctx.post(FAN, {
    headers: auth,
    data: { reserved_date: isoPlus(seed.seedDate, 10), reserved_time: '12:30', party_size: 2 },
  });
  expect(created.status()).toBe(201);
  const body = await created.json();
  expect(body.status).toBe('requested');
  // Fan view omits operator-only fields.
  expect(body.operator_id).toBeUndefined();
  expect(body.fan_id).toBeUndefined();

  const listed = await ctx.get(FAN, { headers: auth });
  expect(listed.status()).toBe(200);
  const ids = (await listed.json()).map((r: { id: string }) => r.id);
  expect(ids).toContain(body.id);
});

test('a blocked fan is refused (ASS-111 enforcement)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(FAN, {
    headers: { authorization: `Bearer ${seed.blockedFanToken}` },
    data: { reserved_date: isoPlus(seed.seedDate, 11) },
  });
  expect(res.status()).toBe(400);
});

test('operator drives confirm then cancel end to end', async () => {
  const ctx = await request.newContext();
  const auth = { authorization: `Bearer ${seed.operatorToken}` };
  const created = await ctx.post(OP, {
    headers: auth,
    data: { fan_id: seed.fanId, reserved_date: isoPlus(seed.seedDate, 20), reserved_time: '18:00' },
  });
  expect(created.status()).toBe(201);
  const id = (await created.json()).id;

  const confirmed = await ctx.post(`${OP}/${id}/confirm`, { headers: auth });
  expect(confirmed.status()).toBe(200);
  expect((await confirmed.json()).status).toBe('confirmed');

  const cancelled = await ctx.post(`${OP}/${id}/cancel`, { headers: auth, data: { reason: 'store closed' } });
  expect(cancelled.status()).toBe(200);
  expect((await cancelled.json()).status).toBe('cancelled');
});

test('a staff token cannot use the fan endpoint (role gate)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(FAN, {
    headers: { authorization: `Bearer ${seed.operatorToken}` },
    data: { reserved_date: isoPlus(seed.seedDate, 30) },
  });
  expect(res.status()).toBe(403);
});

test('the operator surface refuses fan and anonymous callers', async () => {
  const ctx = await request.newContext();
  const fanRes = await ctx.get(OP, { headers: { authorization: `Bearer ${seed.fanToken}` } });
  expect([401, 403]).toContain(fanRes.status());
  const anonRes = await ctx.get(OP);
  expect([401, 403]).toContain(anonRes.status());
});
