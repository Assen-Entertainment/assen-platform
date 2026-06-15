import { test, expect, request } from '@playwright/test';
import * as fs from 'node:fs';

// seed_event_campaign.py writes tokens + a published and a draft campaign id here;
// a regression in publication visibility, block enforcement, or auth fails this gate.
const seedPath = process.env.EVENT_CAMPAIGN_SEED_OUT;
if (!seedPath) {
  throw new Error('EVENT_CAMPAIGN_SEED_OUT must point at the seed JSON written by seed_event_campaign.py');
}
const seed = JSON.parse(fs.readFileSync(seedPath, 'utf-8'));

const OP = '/api/operator/event-campaigns';
const FANC = '/api/fan/event-campaigns';
const FANR = '/api/fan/event-reservations';

function bearer(token: string) {
  return { authorization: `Bearer ${token}` };
}

test('operator sees both the draft and the published campaign', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(OP, { headers: bearer(seed.operatorToken) });
  expect(res.status()).toBe(200);
  const ids = (await res.json()).map((c: { id: string }) => c.id);
  expect(ids).toContain(seed.publishedCampaignId);
  expect(ids).toContain(seed.draftCampaignId);
});

test('fan list shows the published campaign but not the draft', async () => {
  const ctx = await request.newContext();
  const res = await ctx.get(FANC, { headers: bearer(seed.fanToken) });
  expect(res.status()).toBe(200);
  const ids = (await res.json()).map((c: { id: string }) => c.id);
  expect(ids).toContain(seed.publishedCampaignId);
  expect(ids).not.toContain(seed.draftCampaignId);
});

test('a fan views a published campaign but a draft id is 404 (no existence leak)', async () => {
  const ctx = await request.newContext();
  const pub = await ctx.post(`${FANC}/${seed.publishedCampaignId}/view`, { headers: bearer(seed.fanToken) });
  expect(pub.status()).toBe(200);
  const draft = await ctx.post(`${FANC}/${seed.draftCampaignId}/view`, { headers: bearer(seed.fanToken) });
  expect(draft.status()).toBe(404);
});

test('a fan reserves a published campaign, lists it, and cancels it', async () => {
  const ctx = await request.newContext();
  const auth = bearer(seed.fanToken);
  const reserve = await ctx.post(`${FANC}/${seed.publishedCampaignId}/reserve`, {
    headers: auth,
    data: { status: 'reserved' },
  });
  expect(reserve.status()).toBe(201);
  const rid = (await reserve.json()).id;

  const mine = await ctx.get(FANR, { headers: auth });
  expect(mine.status()).toBe(200);
  expect((await mine.json()).map((r: { id: string }) => r.id)).toContain(rid);

  const cancel = await ctx.post(`${FANR}/${rid}/cancel`, { headers: auth });
  expect(cancel.status()).toBe(200);
  expect((await cancel.json()).status).toBe('cancelled');
});

test('a blocked fan cannot reserve (400)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(`${FANC}/${seed.publishedCampaignId}/reserve`, {
    headers: bearer(seed.blockedFanToken),
    data: {},
  });
  expect(res.status()).toBe(400);
});

test('a draft campaign cannot be reserved (404, no existence leak)', async () => {
  const ctx = await request.newContext();
  const res = await ctx.post(`${FANC}/${seed.draftCampaignId}/reserve`, {
    headers: bearer(seed.fanToken),
    data: {},
  });
  expect(res.status()).toBe(404);
});

test('operator publish/unpublish round-trip toggles fan visibility', async () => {
  const ctx = await request.newContext();
  const op = bearer(seed.operatorToken);
  const created = await ctx.post(OP, {
    headers: op,
    data: { title: 'Round Trip', starts_at: new Date(Date.now() + 30 * 864e5).toISOString(), event_type: 'guest_day' },
  });
  expect(created.status()).toBe(201);
  const cid = (await created.json()).id;

  // Draft: hidden from fans.
  let fanIds = (await (await ctx.get(FANC, { headers: bearer(seed.fanToken) })).json()).map((c: { id: string }) => c.id);
  expect(fanIds).not.toContain(cid);

  expect((await ctx.post(`${OP}/${cid}/publish`, { headers: op })).status()).toBe(200);
  fanIds = (await (await ctx.get(FANC, { headers: bearer(seed.fanToken) })).json()).map((c: { id: string }) => c.id);
  expect(fanIds).toContain(cid);

  expect((await ctx.post(`${OP}/${cid}/unpublish`, { headers: op })).status()).toBe(200);
  fanIds = (await (await ctx.get(FANC, { headers: bearer(seed.fanToken) })).json()).map((c: { id: string }) => c.id);
  expect(fanIds).not.toContain(cid);
});

test('a staff token cannot reserve, and the operator surface refuses fan/anon', async () => {
  const ctx = await request.newContext();
  const staffReserve = await ctx.post(`${FANC}/${seed.publishedCampaignId}/reserve`, {
    headers: bearer(seed.operatorToken),
    data: {},
  });
  expect(staffReserve.status()).toBe(403);
  expect([401, 403]).toContain((await ctx.get(OP, { headers: bearer(seed.fanToken) })).status());
  expect([401, 403]).toContain((await ctx.get(OP)).status());
});
