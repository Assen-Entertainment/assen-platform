import type { Metadata } from "next";
import { getCreators, getProducts } from "@/lib/api";
import { DiscoveryView } from "./discovery-view";

export const metadata: Metadata = {
  title: "발견",
  description: "취향에 맞는 크리에이터와 추천 상품을 카테고리·선반으로 둘러보세요.",
  openGraph: { title: "크리에이터 발견 · Assen", description: "취향에 맞는 크리에이터와 상품을 발견하세요.", type: "website" },
};

/** Discovery — 서버 컴포넌트에서 데이터 fetch(현재 mock) → 클라이언트 뷰. 실 API 전환 시 lib/api만 교체. */
export default async function DiscoveryPage() {
  const [creators, products] = await Promise.all([getCreators(), getProducts()]);
  return <DiscoveryView creators={creators} products={products} />;
}
