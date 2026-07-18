import type { Metadata } from "next";
import { getSubscriptions } from "@/lib/api";
import { MembershipView } from "./membership-view";

export const metadata: Metadata = {
  title: "멤버십",
  description: "내 멤버십을 관리하고, 크리에이터를 둘러보며 새 멤버십에 가입해 보세요.",
  openGraph: { title: "멤버십 · Assen", description: "내 멤버십을 관리하고 크리에이터를 둘러보세요.", type: "website" },
};

/**
 * Membership — "내 멤버십 허브". 서버 fetch(내 활성 구독) → 클라 뷰(관리 + 디스커버리 유도).
 * 구독은 항상 크리에이터 컨텍스트(프로필 멤버십 탭)에서만 시작 — 전역 요금표 직접 구독 동선 제거.
 */
export default async function MembershipPage() {
  const subscriptions = await getSubscriptions();
  return <MembershipView subscriptions={subscriptions} />;
}
