import type { Metadata } from "next";
import { getProductsPage } from "@/lib/api";
import { StoreView } from "./store-view";

export const metadata: Metadata = {
  title: "스토어",
  description: "굿즈·디지털·티켓·쿠폰까지, 크리에이터의 다양한 상품을 만나보세요.",
  openGraph: { title: "스토어 · Assen", description: "크리에이터의 굿즈·디지털·티켓 상품을 만나보세요.", type: "website" },
};

/** Store — 서버에서 커서 Page(getProductsPage) 시드 → 클라 뷰(필터+무한 로드). 실 API 전환 시 lib/api만 교체. */
export default async function StorePage() {
  const products = await getProductsPage();
  return <StoreView products={products} />;
}
