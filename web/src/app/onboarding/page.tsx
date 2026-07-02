import { getCreators } from "@/lib/api";
import { OnboardingView } from "./onboarding-view";

/** Onboarding — 관심사→크리에이터 선택→완료. 서버 fetch(creators) → 클라 뷰. 셸 없는 집중 플로우. */
export default async function OnboardingPage() {
  const creators = await getCreators();
  return <OnboardingView creators={creators} />;
}
