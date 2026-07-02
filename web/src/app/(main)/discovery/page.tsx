import { getCreators, getProducts } from "@/lib/api";
import { DiscoveryView } from "./discovery-view";

/** Discovery — 서버 컴포넌트에서 데이터 fetch(현재 mock) → 클라이언트 뷰. 실 API 전환 시 lib/api만 교체. */
export default async function DiscoveryPage() {
  const [creators, products] = await Promise.all([getCreators(), getProducts()]);
  return <DiscoveryView creators={creators} products={products} />;
}
