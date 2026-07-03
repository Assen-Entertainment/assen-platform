import { getSubscriptions } from "@/lib/api";
import { SubscriptionsView } from "./subscriptions-view";

/** 구독 관리 — 서버 fetch(mock) → 클라 뷰(해지 확인 시트). */
export default async function SubscriptionsPage() {
  const subscriptions = await getSubscriptions();
  return <SubscriptionsView subscriptions={subscriptions} />;
}
