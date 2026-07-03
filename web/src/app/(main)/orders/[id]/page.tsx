import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getOrder } from "@/lib/api";
import { OrderDetailView } from "./order-detail-view";

/** 주문 상세 — 동적 라우트(/orders/[id]). 서버 fetch → 클라 뷰(취소·환불 mock 전환). */
export default async function OrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const order = await getOrder(id);
  if (!order) notFound();
  return <OrderDetailView order={order} />;
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  return { title: `주문 ${id}` };
}
