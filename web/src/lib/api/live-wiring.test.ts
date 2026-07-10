import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  apiToggleLike,
  apiCreateOrder,
  apiCancelSubscription,
  apiChangeSubscriptionTier,
  apiMarkNotificationRead,
  apiReport,
  apiAddPaymentMethod,
  apiCreateStudioProduct,
  apiUpdateStudioTier,
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

  it("apiCreateOrder(배송): shipping 배송지를 snake로 전송 + shipping_fee·shipping_address 매핑", async () => {
    const f = mockJson(201, {
      id: "o2",
      status: "paid",
      created_at: "2026-07-05T10:00:00Z",
      items: [{ product_id: "p1", title: "아크릴 스탠드", type: "goods", option: "", price: 18000, qty: 1 }],
      subtotal: 18000,
      shipping: 0,
      shipping_fee: 0,
      total: 18000,
      creator_name: "별빛 일러스트",
      shipping_address: {
        recipient_name: "홍길동",
        recipient_phone: "010-1234-5678",
        postal_code: "04524",
        address1: "서울 중구 세종대로 110",
        address2: "1203호",
      },
      refund: null,
    });
    vi.stubGlobal("fetch", f);

    const order = await apiCreateOrder({
      productId: "p1",
      qty: 1,
      shipping: {
        recipientName: "홍길동",
        recipientPhone: "010-1234-5678",
        postalCode: "04524",
        address1: "서울 중구 세종대로 110",
        address2: "1203호",
      },
    });
    // 응답 매핑: shipping_fee 우선 소비 + 배송지 스냅샷 camelCase.
    expect(order.shipping).toBe(0);
    expect(order.shippingAddress).toEqual({
      recipientName: "홍길동",
      recipientPhone: "010-1234-5678",
      postalCode: "04524",
      address1: "서울 중구 세종대로 110",
      address2: "1203호",
    });
    // 요청 페이로드는 snake — raw camel 필드는 전송하지 않는다.
    const [, init] = (f as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(JSON.parse(init.body).shipping).toEqual({
      recipient_name: "홍길동",
      recipient_phone: "010-1234-5678",
      postal_code: "04524",
      address1: "서울 중구 세종대로 110",
      address2: "1203호",
    });
  });

  it("apiChangeSubscriptionTier: PATCH /subscriptions/{id} {tier_id} 전송 + SubscriptionOut 매핑", async () => {
    const f = mockJson(200, {
      id: "s1",
      creator_id: "c1",
      creator_name: "별빛 일러스트",
      creator_handle: "stellar",
      tier_id: "t3",
      tier_name: "프리미엄",
      price: 19900,
      period: "월",
      status: "active",
      next_billing_date: "2026-08-01",
      cancel_scheduled: false,
    });
    vi.stubGlobal("fetch", f);

    const sub = await apiChangeSubscriptionTier("s1", "t3");
    expect(sub.tierId).toBe("t3");
    expect(sub.tierName).toBe("프리미엄");
    expect(sub.price).toBe(19900);

    const [url, init] = (f as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(String(url)).toContain("/subscriptions/s1");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body)).toEqual({ tier_id: "t3" });
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

describe("결제수단 PCI(R4) — raw 카드 미전송", () => {
  it("apiAddPaymentMethod: brand + mock PG 토큰만 전송하고 raw PAN/CVC/expiry는 절대 보내지 않는다", async () => {
    const f = mockJson(201, { id: "pm1", brand: "신한카드", last4: "1234", is_primary: true, created_at: "2026-07-03T10:00:00Z" });
    vi.stubGlobal("fetch", f);

    const method = await apiAddPaymentMethod({ brand: "신한카드", makePrimary: true });
    expect(method).toEqual({ id: "pm1", brand: "신한카드", last4: "1234", isPrimary: true, createdAt: "2026-07-03T10:00:00Z" });

    const [url, init] = (f as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(String(url)).toContain("/fan/payment-methods");
    const body = JSON.parse(init.body);
    // 정확히 brand·card_number·make_primary만 — 카드번호는 mock 토큰, CVC/유효기간 필드는 없음.
    expect(Object.keys(body).sort()).toEqual(["brand", "card_number", "make_primary"]);
    expect(body.brand).toBe("신한카드");
    expect(body.make_primary).toBe(true);
    expect(body.card_number).toMatch(/^pg_mock_tok_/);
    expect(body).not.toHaveProperty("cvc");
    expect(body).not.toHaveProperty("expiry");
  });
});

describe("스튜디오 카탈로그 쓰기 매핑", () => {
  it("apiCreateStudioProduct: StudioProductOut snake→StudioProduct(sold 실값·updatedAt 파생)", async () => {
    const f = mockJson(201, {
      id: "sp1",
      creator_id: "c1",
      type: "goods",
      title: "굿즈",
      price: 10000,
      meta: "",
      media_url: "",
      description: "",
      options: [],
      stock: 50,
      sold_out: false,
      locked: false,
      status: "draft",
      is_adult: false,
      created_at: new Date().toISOString(),
      sold: 0,
    });
    vi.stubGlobal("fetch", f);

    const p = await apiCreateStudioProduct({ type: "goods", title: "굿즈", price: 10000 });
    expect(p.id).toBe("sp1");
    expect(p.status).toBe("draft");
    // ASS-264: 서버가 비취소 주문 기준 실 판매수를 반환 — 카운트만(수익 금액 아님).
    expect(p.sold).toBe(0);
    expect(p.stock).toBe(50);
    expect(typeof p.updatedAt).toBe("string");

    const [, init] = (f as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toMatchObject({ type: "goods", title: "굿즈", price: 10000, status: "draft" });
  });

  it("apiUpdateStudioTier: 제공 필드만 PATCH 전송 + StudioTier(subscribers 실값) 매핑", async () => {
    const f = mockJson(200, {
      id: "t1",
      creator_id: "c1",
      name: "베이직",
      price: 5000,
      period: "월",
      benefits: ["멤버 전용 포스트"],
      badge: "",
      featured: false,
      active: false,
      sort_order: 0,
      created_at: new Date().toISOString(),
      subscribers: 3,
    });
    vi.stubGlobal("fetch", f);

    const t = await apiUpdateStudioTier("t1", { active: false });
    expect(t.active).toBe(false);
    // ASS-264: 서버가 활성(status=active) 구독자 실 카운트를 반환 — 수익 금액 아님.
    expect(t.subscribers).toBe(3);
    expect(t.name).toBe("베이직");

    const [url, init] = (f as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(String(url)).toContain("/studio/tiers/t1");
    expect(init.method).toBe("PATCH");
    // undefined 필드는 직렬화에서 제거 → active만 전송.
    expect(JSON.parse(init.body)).toEqual({ active: false });
  });
});
