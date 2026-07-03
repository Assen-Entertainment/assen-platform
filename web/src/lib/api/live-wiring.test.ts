import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  apiToggleLike,
  apiCreateOrder,
  apiCancelSubscription,
  apiMarkNotificationRead,
  apiReport,
} from "./index";

/**
 * 실 호출 경로(뮤테이션 API) 검증 — snake→camel 매핑, accepted→approved, 알림 파생,
 * CSRF 헤더 부착. apiFetch는 config.apiUrl과 무관하게 직접 호출되므로 fetch만 목킹한다.
 * (getOrders 등 USE_API 분기 함수와 달리 매퍼 자체를 직접 검증.)
 */

function mockJson(status: number, payload: unknown) {
  return vi.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(payload),
  })) as unknown as typeof fetch;
}

beforeEach(() => {
  // csrftoken 쿠키를 심어 /fan/csrf 프라이밍을 건너뛴다(단일 fetch 호출 보장).
  document.cookie = "csrftoken=testtok";
});
afterEach(() => {
  vi.restoreAllMocks();
});

describe("CSRF double-submit", () => {
  it("불안전 메서드에 X-CSRFToken 헤더와 credentials:include를 붙인다", async () => {
    const f = mockJson(200, { liked: true, like_count: 43 });
    vi.stubGlobal("fetch", f);

    const res = await apiToggleLike("po1", true);
    expect(res).toEqual({ liked: true, like_count: 43 });

    const [, init] = (f as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(init.method).toBe("PUT");
    expect(init.credentials).toBe("include");
    expect(init.headers["X-CSRFToken"]).toBe("testtok");
  });
});

describe("커머스/구독/알림 매핑", () => {
  it("apiCreateOrder: OrderOut snake→camel, 환불 accepted→approved, 날짜 YYYY-MM-DD", async () => {
    vi.stubGlobal(
      "fetch",
      mockJson(201, {
        id: "o1",
        status: "paid",
        created_at: "2026-07-03T10:00:00Z",
        items: [{ product_id: "p1", title: "아크릴 스탠드", type: "goods", option: "", price: 18000, qty: 2 }],
        subtotal: 36000,
        shipping: 3000,
        total: 39000,
        creator_name: "별빛 일러스트",
        refund: { status: "accepted", reason: "단순 변심" },
      }),
    );

    const order = await apiCreateOrder({ productId: "p1", qty: 2 });
    expect(order.id).toBe("o1");
    expect(order.createdAt).toBe("2026-07-03");
    expect(order.items[0]).toEqual({ productId: "p1", title: "아크릴 스탠드", type: "goods", price: 18000, qty: 2 });
    expect(order.creatorName).toBe("별빛 일러스트");
    expect(order.refund?.status).toBe("approved");
  });

  it("apiCancelSubscription: cancel_scheduled→cancelScheduled 매핑", async () => {
    vi.stubGlobal(
      "fetch",
      mockJson(200, {
        id: "s1",
        creator_id: "c1",
        creator_name: "별빛 일러스트",
        creator_handle: "stellar",
        tier_id: "t2",
        tier_name: "스탠다드",
        price: 9900,
        period: "월",
        status: "active",
        next_billing_date: "2026-08-01",
        cancel_scheduled: true,
      }),
    );

    const sub = await apiCancelSubscription("s1");
    expect(sub.cancelScheduled).toBe(true);
    expect(sub.status).toBe("active");
    expect(sub.creatorHandle).toBe("stellar");
    expect(sub.nextBillingDate).toBe("2026-08-01");
  });

  it("apiMarkNotificationRead: 미지의 kind→system, group/time 파생", async () => {
    vi.stubGlobal(
      "fetch",
      mockJson(200, {
        id: "n1",
        kind: "unknown_kind",
        title: "알림 제목",
        href: "/post/po1",
        read: true,
        created_at: new Date().toISOString(),
      }),
    );

    const n = await apiMarkNotificationRead("n1");
    expect(n.kind).toBe("system");
    expect(n.group).toBe("today");
    expect(n.href).toBe("/post/po1");
    expect(n.read).toBe(true);
    expect(typeof n.time).toBe("string");
  });

  it("apiReport: report_type 페이로드 전송 + 응답 camelCase 매핑", async () => {
    const f = mockJson(201, { safety_report_id: "r1", status: "received", created_at: "2026-07-03T10:00:00Z" });
    vi.stubGlobal("fetch", f);

    const result = await apiReport({ reportType: "spam", narrative: "도배성 홍보" });
    expect(result).toEqual({ safetyReportId: "r1", status: "received", createdAt: "2026-07-03T10:00:00Z" });

    const [url, init] = (f as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(String(url)).toContain("/safety/fan-reports");
    expect(JSON.parse(init.body)).toEqual({ report_type: "spam", narrative: "도배성 홍보" });
  });
});
