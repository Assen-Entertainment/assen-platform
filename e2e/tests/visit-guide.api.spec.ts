import { test, expect, request } from '@playwright/test';
import * as fs from 'node:fs';

// seed_visit_guide.py writes tokens + a published and a draft section id here.
// This gate proves publication visibility, the unauthenticated public read, the
// draft 404 (no existence leak), the fan rule acknowledgement, and the gates.
const seedPath = process.env.VISIT_GUIDE_SEED_OUT;
if (!seedPath) {
  throw new Error('VISIT_GUIDE_SEED_OUT must point at the seed JSON written by seed_visit_guide.py');
}
const seed = JSON.parse(fs.readFileSync(seedPath, 'utf-8'));

const OP = '/api/operator/visit-guide';
const PUB = '/api/visit-guide';
const FAN = '/api/fan/visit-guide';

function bearer(token: string) {
  return { authorization: `Bearer ${token}` };
}

test('operator sees both the draft and the published section', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(OP, { headers: bearer(seed.operatorToken) });
  expect(res.status()).toBe(200);
  const ids = (await res.json()).map((s: { id: string }) => s.id);
  expect(ids).toContain(seed.publishedSectionId);
  expect(ids).toContain(seed.draftSectionId);
});

test('the public list shows the published section but not the draft (no auth)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(PUB); // no auth header
  expect(res.status()).toBe(200);
  const ids = (await res.json()).map((s: { id: string }) => s.id);
  expect(ids).toContain(seed.publishedSectionId);
  expect(ids).not.toContain(seed.draftSectionId);
});

test('a published section reads publicly but a draft id is 404 (no existence leak)', async () => {
  const ctx = await request.newContext();
  const pub = await ctx.get(`${PUB}/${seed.publishedSectionId}`);
  expect(pub.status()).toBe(200);
  const body = await pub.json();
  expect(body.section_type).toBe('usage_rules');
  expect(body.created_by_id).toBeUndefined(); // no operator-only field
  const draft = await ctx.get(`${PUB}/${seed.draftSectionId}`);
  expect(draft.status()).toBe(404);
});

test('a fan acknowledges the published usage rules at the version they read', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(`${FAN}/acknowledge-rules`, {
    headers: bearer(seed.fanToken),
    data: { version: 1 },
  });
  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(body.acknowledged).toBe(true);
  expect(body.version).toBe(1);
});

test('a stale rules version acknowledgement is refused (409)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(`${FAN}/acknowledge-rules`, {
    headers: bearer(seed.fanToken),
    data: { version: 999 },
  });
  expect(res.status()).toBe(409);
});

test('a published section cannot be edited in place (400); unpublish first', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(`${OP}/${seed.publishedSectionId}/update`, {
    headers: bearer(seed.operatorToken),
    data: { title: 'sneaky edit' },
  });
  expect(res.status()).toBe(400);
});

test('a staff token cannot acknowledge, and the operator surface refuses fan/anon', async () => {
  const ctx = await request.newContext();
  const staffAck = await ctx.post(`${FAN}/acknowledge-rules`, {
    headers: bearer(seed.operatorToken),
    data: { version: 1 },
  });
  expect(staffAck.status()).toBe(403);
  expect([401, 403]).toContain((await ctx.get(OP, { headers: bearer(seed.fanToken) })).status());
  expect([401, 403]).toContain((await ctx.get(OP)).status());
});

test('publish/unpublish round-trip toggles public visibility', async () => {
  const ctx = await request.newContext();
  const op = bearer(seed.operatorToken);
  // Create a fresh draft of a not-yet-used type, publish, then unpublish.
  const created = await ctx.post(OP, {
    headers: op,
    data: { section_type: 'operating_hours', title: '이용 시간' },
  });
  expect(created.status()).toBe(201);
  const sid = (await created.json()).id;

  let pubIds = (await (await ctx.get(PUB)).json()).map((s: { id: string }) => s.id);
  expect(pubIds).not.toContain(sid);

  expect((await ctx.post(`${OP}/${sid}/publish`, { headers: op })).status()).toBe(200);
  pubIds = (await (await ctx.get(PUB)).json()).map((s: { id: string }) => s.id);
  expect(pubIds).toContain(sid);

  expect((await ctx.post(`${OP}/${sid}/unpublish`, { headers: op })).status()).toBe(200);
  pubIds = (await (await ctx.get(PUB)).json()).map((s: { id: string }) => s.id);
  expect(pubIds).not.toContain(sid);
});
