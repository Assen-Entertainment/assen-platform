import { getOrders } from "@/lib/api";
import { OrdersView } from "./orders-view";

/** Orders — 주문 내역. 서버 fetch(lib/api) → 클라 뷰(initialData 하이드레이션 + 커서 더보기). */
export default async function OrdersPage() {
  const orders = await getOrders();
  return <OrdersView initialOrders={orders} />;
}
