import type { Metadata } from "next";
import { getMembershipTiers } from "@/lib/api";
import { MembershipView } from "./membership-view";

export const metadata: Metadata = {
  title: "멤버십",
  description: "크리에이터를 정기 후원하고 전용 혜택을 받는 멤버십 티어를 둘러보세요.",
  openGraph: { title: "멤버십 · Assen", description: "크리에이터를 정기 후원하고 전용 혜택을 받아보세요.", type: "website" },
};

/** Membership — 멤버십 티어 둘러보기. 서버 fetch(tiers) → 클라 뷰(구독 CTA→체크아웃). */
export default async function MembershipPage() {
  const tiers = await getMembershipTiers();
  return <MembershipView tiers={tiers} />;
}
