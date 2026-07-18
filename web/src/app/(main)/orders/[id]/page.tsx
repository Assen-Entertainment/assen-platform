import type { Metadata } from "next";
import { OrderDetailClient } from "./order-detail-view";

/**
 * 주문 상세 — 동적 라우트(/orders/[id]). 보호 라우트라 클라이언트에서 조회한다: SSR로 await getOrder →
 * notFound()를 하면, 만료된 access 쿠키(유효 refresh 세션)가 낸 401이 가짜 404가 된다(SSR-401≠404).
 * 클라 useOrder가 api client의 401 refresh-and-retry를 소유해 만료 세션을 실 주문으로 복구한다.
 */
export default async function OrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <OrderDetailClient id={id} />;
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  return { title: `주문 ${id}` };
}
