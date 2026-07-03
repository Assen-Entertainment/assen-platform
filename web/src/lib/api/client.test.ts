import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { apiFetch, ApiError } from "./client";

/**
 * apiFetch 클라이언트 계약 — 비정상 응답 detail 보존(C1)과 401 refresh-and-retry(C11).
 * config.apiUrl 미설정(테스트) → base="" 이므로 URL은 경로 그대로("/orders" 등).
 */

beforeEach(() => {
  // csrftoken 쿠키를 심어 /fan/csrf 프라이밍을 건너뛴다(불안전 메서드 단일 fetch 보장).
  document.cookie = "csrftoken=testtok";
});
afterEach(() => {
  vi.restoreAllMocks();
});

describe("ApiError detail 보존", () => {
  it("비정상 응답 본문 {detail}을 ApiError.detail로 파싱한다", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 422,
        text: async () => JSON.stringify({ detail: "이미 구독 중이에요." }),
      })),
    );

    const err = await apiFetch("/subscriptions", { method: "POST", body: "{}" }).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(422);
    expect(err.detail).toBe("이미 구독 중이에요.");
  });

  it("비-JSON/비객체 본문은 detail=undefined로 둔다", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 500, text: async () => "<html>500</html>" })),
    );

    const err = await apiFetch("/orders").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(500);
    expect(err.detail).toBeUndefined();
  });
});

describe("401 refresh-and-retry", () => {
  it("401이면 POST /fan/refresh 후 원 요청을 1회 재시도해 성공한다", async () => {
    const calls: string[] = [];
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      calls.push(`${(init?.method ?? "GET").toUpperCase()} ${url}`);
      if (url.endsWith("/fan/refresh")) {
        return { ok: true, status: 200, text: async () => "" };
      }
      // 원 요청: 최초는 401, refresh 후 재시도는 200.
      const attempts = calls.filter((c) => c.endsWith("/orders")).length;
      if (attempts < 2) return { ok: false, status: 401, text: async () => "" };
      return { ok: true, status: 200, text: async () => JSON.stringify({ items: [], next_cursor: null }) };
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await apiFetch<{ items: unknown[]; next_cursor: string | null }>("/orders");
    expect(res).toEqual({ items: [], next_cursor: null });

    // 순서: /orders(401) → /fan/refresh(200) → /orders(200) — refresh 1회, 원 요청 2회.
    expect(calls.filter((c) => c.includes("/fan/refresh")).length).toBe(1);
    expect(calls.filter((c) => c.endsWith("/orders")).length).toBe(2);
  });

  it("refresh 자체가 401이면 재시도하지 않고 원 401을 전파한다", async () => {
    const calls: string[] = [];
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      calls.push(`${(init?.method ?? "GET").toUpperCase()} ${url}`);
      // 원 요청·refresh 모두 401(로그인 안 됨).
      return { ok: false, status: 401, text: async () => "" };
    });
    vi.stubGlobal("fetch", fetchMock);

    const err = await apiFetch("/orders").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(401);
    // /orders 1회 + /fan/refresh 1회 = 재시도 없음(refresh 실패 → 원 401 전파).
    expect(calls.filter((c) => c.endsWith("/orders")).length).toBe(1);
    expect(calls.filter((c) => c.includes("/fan/refresh")).length).toBe(1);
  });
});
