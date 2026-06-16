import { test, expect, request } from '@playwright/test';
import * as fs from 'node:fs';

// seed_rbac.py writes admin/operator/fan tokens + account ids here. This gate
// proves admin role assignment, the fail-closed conflicts (last-admin, no-op),
// invalid-role rejection, and the admin-only gate. Run serially (--workers=1):
// the role transitions are ordered and the service row-locks (sqlite single
// writer). HUMAN-REVIEW-REQUIRED: authz surface (#26).
const seedPath = process.env.RBAC_SEED_OUT;
if (!seedPath) {
  throw new Error('RBAC_SEED_OUT must point at the seed JSON written by seed_rbac.py');
}
const seed = JSON.parse(fs.readFileSync(seedPath, 'utf-8'));

const ROLES = '/api/admin/rbac/roles';

function bearer(token: string) {
  return { authorization: `Bearer ${token}` };
}

function assign(ctx: any, token: string, accountId: string, role: string) {
  return ctx.post(ROLES, {
    headers: bearer(token),
    data: { account_id: accountId, role, reason: 'e2e role change' },
  });
}

test.describe.configure({ mode: 'serial' });

test('admin promotes a fan to operator', async () => {
  const ctx = await request.newContext();
  const res = await assign(ctx, seed.adminToken, seed.targetFanId, 'operator');
  expect(res.status()).toBe(200);
  expect((await res.json()).role).toBe('operator');
});

test('an unassignable role (cast) is refused (400)', async () => {
  const ctx = await request.newContext();
  const res = await assign(ctx, seed.adminToken, seed.targetFanId, 'cast');
  expect(res.status()).toBe(400);
});

test('a no-op assignment is refused (409)', async () => {
  const ctx = await request.newContext();
  // targetFan is now operator (from the first test); re-assigning operator is a no-op.
  const res = await assign(ctx, seed.adminToken, seed.targetFanId, 'operator');
  expect(res.status()).toBe(409);
});

test('a role change without a reason is refused (422)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(ROLES, {
    headers: bearer(seed.adminToken),
    data: { account_id: seed.targetFanId, role: 'manager' }, // no reason
  });
  expect(res.status()).toBe(422);
});

test('demoting a second admin is allowed while another admin remains', async () => {
  const ctx = await request.newContext();
  const res = await assign(ctx, seed.adminToken, seed.secondAdminId, 'manager');
  expect(res.status()).toBe(200);
  expect((await res.json()).role).toBe('manager');
});

test('demoting the last admin (acting admin) is refused (409)', async () => {
  const ctx = await request.newContext();
  // After the previous test the acting admin is the sole admin.
  const res = await assign(ctx, seed.adminToken, seed.adminId, 'operator');
  expect(res.status()).toBe(409);
});

test('the staff list returns staff accounts', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(ROLES, { headers: bearer(seed.adminToken) });
  expect(res.status()).toBe(200);
  const ids = (await res.json()).map((r: { account_id: string }) => r.account_id);
  expect(ids).toContain(seed.adminId);
});

test('non-admin and anonymous callers are refused', async () => {
  const ctx = await request.newContext();
  expect([401, 403]).toContain((await ctx.get(ROLES, { headers: bearer(seed.operatorToken) })).status());
  expect([401, 403]).toContain((await ctx.get(ROLES, { headers: bearer(seed.fanToken) })).status());
  expect([401, 403]).toContain((await ctx.get(ROLES)).status());
});
