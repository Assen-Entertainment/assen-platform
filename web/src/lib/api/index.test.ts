import { describe, it, expect } from "vitest";
import { getFeed, getSearch, getProducts, getMembershipTiers, getPost } from "./index";

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
