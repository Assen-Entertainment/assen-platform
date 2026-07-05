import { describe, it, expect } from "vitest";
import {
  getFeed,
  getSearch,
  getProducts,
  getProduct,
  getMembershipTiers,
  getPost,
  getOrders,
  getOrder,
  getNotifications,
  getSubscriptions,
  getBlocks,
  getCreator,
  getStudioStats,
  mockSetBlocked,
} from "./index";

// NEXT_PUBLIC_API_URL 미설정(테스트 환경) → mock 폴백 경로를 검증한다.
describe("lib/api mock fallback", () => {
  it("getFeed는 전체 포스트를 반환한다", async () => {
    const posts = await getFeed();
    expect(posts.length).toBe(6);
    expect(posts[0]).toHaveProperty("likeCount");
  });

  it("getSearch는 name/handle·title 부분일치로 필터한다(서버 의미론 미러)", async () => {
    const byName = await getSearch("Neon");
    expect(byName.creators.map((c) => c.handle)).toContain("neonbeats");
    const byHandle = await getSearch("stellar");
    expect(byHandle.creators.map((c) => c.handle)).toContain("stellar");
    const byTitle = await getSearch("아크릴");
    expect(byTitle.products.map((p) => p.title)).toContain("아크릴 스탠드");
  });

  it("getSearch는 빈 질의에 빈 결과를 반환한다", async () => {
    expect(await getSearch("  ")).toEqual({ creators: [], products: [] });
  });

  it("getProducts/getMembershipTiers는 creatorId 스코프를 존중한다", async () => {
    expect((await getProducts("c1")).length).toBe(4);
    expect(await getProducts("c2")).toEqual([]);
    expect((await getMembershipTiers("c1")).length).toBe(3);
    expect(await getMembershipTiers("c2")).toEqual([]);
  });

  it("getPost는 미지의 id에 undefined를 반환한다(notFound 계약)", async () => {
    expect(await getPost("nope")).toBeUndefined();
  });
});

describe("커머스 mock (W2)", () => {
  it("getProduct는 목록에서 id로 find 폴백한다", async () => {
    const p = await getProduct("p1");
    expect(p?.title).toBe("아크릴 스탠드");
    expect(await getProduct("nope")).toBeUndefined();
  });

  it("getOrders/getOrder는 주문을 반환하고 미지의 id는 undefined(notFound 계약)", async () => {
    const orders = await getOrders();
    expect(orders.length).toBeGreaterThan(0);
    const first = orders[0];
    expect(await getOrder(first.id)).toEqual(first);
    // 합계 = 소계 + 배송비 (mock 데이터 정합성)
    expect(first.total).toBe(first.subtotal + first.shipping);
    expect(await getOrder("ASN-0000")).toBeUndefined();
  });

  it("getNotifications는 그룹/종류 필드를 가진 알림을 반환한다", async () => {
    const list = await getNotifications();
    expect(list.length).toBeGreaterThan(0);
    expect(list.every((n) => n.group === "today" || n.group === "earlier")).toBe(true);
  });

  it("getSubscriptions는 활성 구독을 반환한다", async () => {
    const subs = await getSubscriptions();
    expect(subs.length).toBeGreaterThan(0);
    expect(subs[0]).toHaveProperty("nextBillingDate");
  });
});

describe("스튜디오 대시보드 스탯 mock (R4-W5)", () => {
  it("getStudioStats는 결정적 실 카운트를 camelCase로 반환한다(수익/금액 필드 없음)", async () => {
    const stats = await getStudioStats();
    expect(stats).not.toBeNull();
    // camelCase 계약 키(products_selling→productsSelling) — 전부 정수 카운트.
    expect(Object.keys(stats!).sort()).toEqual([
      "followers",
      "orders",
      "posts",
      "products",
      "productsSelling",
      "subscribers",
    ]);
    expect(Object.values(stats!).every((v) => Number.isInteger(v))).toBe(true);
    // 기존 mock 대시보드 수치와 일관(회귀 0) — 팔로워 12,400은 구 하드코딩 카드와 일치.
    expect(stats!.followers).toBe(12400);
    // 판매중은 전체 상품 수의 부분집합.
    expect(stats!.productsSelling).toBeLessThanOrEqual(stats!.products);
    // 서버 계약에 수익/금액 없음(정산 게이트) — mock도 금액을 날조하지 않는다.
    expect(stats).not.toHaveProperty("revenue");
  });
});

describe("차단 mock (R4-W3)", () => {
  it("mockSetBlocked로 차단하면 getBlocks·getCreator(blocked)에 반영되고, 해제하면 사라진다", async () => {
    expect(await getBlocks()).toEqual([]);

    mockSetBlocked("c1", true);
    const list = await getBlocks();
    expect(list.map((b) => b.handle)).toContain("stellar");
    expect((await getCreator("stellar"))?.blocked).toBe(true);

    // 해제 → 목록에서 사라지고 blocked=false.
    mockSetBlocked("c1", false);
    expect(await getBlocks()).toEqual([]);
    expect((await getCreator("stellar"))?.blocked).toBe(false);
  });
});
