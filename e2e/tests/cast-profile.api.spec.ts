import { test, expect, type APIRequestContext } from '@playwright/test';
import { readFileSync } from 'node:fs';

// Cast CRUD writes to the throwaway sqlite harness DB; serialise so concurrent
// writers do not hit "database is locked" under fullyParallel. Production is
// postgres, where this is a non-issue.
test.describe.configure({ mode: 'serial' });

// seed_cast.py writes the three role tokens (operator creates/edits, manager
// grants consent, fan views). Absent → the whole file skips (run the seed first).
type Seed = { operatorToken: string; managerToken: string; fanToken: string };

function loadSeed(): Seed | null {
  try {
    const raw = readFileSync(process.env.CAST_SEED_OUT ?? '.cast_seed.json', 'utf8');
    return JSON.parse(raw) as Seed;
  } catch {
    return null;
  }
}

const SEED = loadSeed();
test.skip(!SEED, 'no seeded cast tokens (.cast_seed.json) — run seed_cast.py first');

function bearer(token: string): Record<string, string> {
  return { authorization: `Bearer ${token}` };
}

async function createProfile(
  request: APIRequestContext,
  operatorToken: string,
  stageName = '미라이',
): Promise<string> {
  const res = await request.post('/api/cast/profiles', {
    headers: bearer(operatorToken),
    data: { stage_name: stageName },
  });
  expect(res.status()).toBe(201);
  return (await res.json()).cast_id as string;
}

async function setVisibility(
  request: APIRequestContext,
  operatorToken: string,
  castId: string,
  visibility: string,
): Promise<void> {
  const res = await request.patch(`/api/cast/profiles/${castId}`, {
    headers: bearer(operatorToken),
    data: { visibility },
  });
  expect(res.status()).toBe(200);
}

async function grant(
  request: APIRequestContext,
  managerToken: string,
  castId: string,
  scope: string,
): Promise<void> {
  const res = await request.post(`/api/cast/profiles/${castId}/consent`, {
    headers: bearer(managerToken),
    data: { scope, status: 'granted' },
  });
  expect(res.status()).toBe(200);
}

test('an operator creates a profile that starts private and hidden', async ({ request }) => {
  const { operatorToken, fanToken } = SEED!;
  const castId = await createProfile(request, operatorToken);

  const detail = await request.get(`/api/cast/profiles/${castId}`, {
    headers: bearer(operatorToken),
  });
  expect(detail.status()).toBe(200);
  const body = await detail.json();
  expect(body.visibility).toBe('private');
  expect(body.consents.stage_name).toBe('withheld');

  // Fail-closed: a fan cannot see the unpublished/unconsented profile (404 so
  // its existence is not even disclosed).
  const fanView = await request.get(`/api/cast/public-profiles/${castId}`, {
    headers: bearer(fanToken),
  });
  expect(fanView.status()).toBe(404);
});

test('a fan sees a profile only after it is published and name-consented', async ({ request }) => {
  const { operatorToken, managerToken, fanToken } = SEED!;
  const castId = await createProfile(request, operatorToken);

  // Published but name not consented → still hidden.
  await setVisibility(request, operatorToken, castId, 'public');
  let fanView = await request.get(`/api/cast/public-profiles/${castId}`, {
    headers: bearer(fanToken),
  });
  expect(fanView.status()).toBe(404);

  // Manager grants the name scope → now visible.
  await grant(request, managerToken, castId, 'stage_name');
  fanView = await request.get(`/api/cast/public-profiles/${castId}`, {
    headers: bearer(fanToken),
  });
  expect(fanView.status()).toBe(200);
  const body = await fanView.json();
  expect(body.stage_name).toBe('미라이');
  // Photo not consented → withheld even though the profile is visible.
  expect(body.photo_ref).toBe('');
});

test('each scope is gated independently', async ({ request }) => {
  const { operatorToken, managerToken, fanToken } = SEED!;
  const castId = await createProfile(request, operatorToken, '사쿠라');
  await setVisibility(request, operatorToken, castId, 'public');
  await grant(request, managerToken, castId, 'stage_name');

  // Operator sets a photo reference and a content scope, but neither scope is
  // granted yet — both are cast-attributable content, so both stay withheld.
  const patched = await request.patch(`/api/cast/profiles/${castId}`, {
    headers: bearer(operatorToken),
    data: { photo_ref: 'cast/sakura.jpg', content_scope: '라이브, 굿즈' },
  });
  expect(patched.status()).toBe(200);

  let body = await (
    await request.get(`/api/cast/public-profiles/${castId}`, { headers: bearer(fanToken) })
  ).json();
  expect(body.photo_ref).toBe('');
  expect(body.content_scope).toBe('');

  // Grant each scope → its field is exposed, independently of the others.
  await grant(request, managerToken, castId, 'profile_photo');
  await grant(request, managerToken, castId, 'content_scope');
  body = await (
    await request.get(`/api/cast/public-profiles/${castId}`, { headers: bearer(fanToken) })
  ).json();
  expect(body.photo_ref).toBe('cast/sakura.jpg');
  expect(body.content_scope).toBe('라이브, 굿즈');
});

test('recording consent requires a manager', async ({ request }) => {
  const { operatorToken } = SEED!;
  const castId = await createProfile(request, operatorToken);
  // The rights gate is manager-only; an operator cannot grant consent.
  const res = await request.post(`/api/cast/profiles/${castId}/consent`, {
    headers: bearer(operatorToken),
    data: { scope: 'stage_name', status: 'granted' },
  });
  expect([401, 403]).toContain(res.status());
});

test('a fan cannot create a cast profile', async ({ request }) => {
  const { fanToken } = SEED!;
  const res = await request.post('/api/cast/profiles', {
    headers: bearer(fanToken),
    data: { stage_name: '미라이' },
  });
  expect([401, 403]).toContain(res.status());
});

test('the fan view rejects a staff token (role gate)', async ({ request }) => {
  const { operatorToken, managerToken } = SEED!;
  const castId = await createProfile(request, operatorToken);
  await setVisibility(request, operatorToken, castId, 'public');
  await grant(request, managerToken, castId, 'stage_name');
  // Visible now, so only the FAN-role gate can refuse the staff caller — a staff
  // token must not be recorded as a fan impression (cast_profile_viewed).
  const res = await request.get(`/api/cast/public-profiles/${castId}`, {
    headers: bearer(operatorToken),
  });
  expect(res.status()).toBe(403);
});

test('the fan view requires authentication', async ({ request }) => {
  const { operatorToken } = SEED!;
  const castId = await createProfile(request, operatorToken);
  const res = await request.get(`/api/cast/public-profiles/${castId}`);
  expect([401, 403]).toContain(res.status());
});
