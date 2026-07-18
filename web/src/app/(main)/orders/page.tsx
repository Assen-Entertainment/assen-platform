import { getOrdersPage } from "@/lib/api";
import { OrdersView } from "./orders-view";

/** Orders — 주문 내역. 서버에서 커서 Page(getOrdersPage) 시드 → 클라 뷰(무한 로드 + 더보기). */
export default async function OrdersPage() {
  const orders = await getOrdersPage();
  return <OrdersView initialOrders={orders} />;
}
