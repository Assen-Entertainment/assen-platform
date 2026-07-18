import type { Metadata } from "next";
import { getFeedPage } from "@/lib/api";
import { FeedView } from "./feed-view";

export const metadata: Metadata = {
  title: "피드",
  description: "팔로우한 크리에이터의 최신 포스트를 한곳에서 확인하세요.",
};

/**
 * Feed — 팔로잉 피드. 서버에서 커서 Page(getFeedPage) 시드 → 클라 뷰(initialData 하이드레이션).
 * Page형 시드라 nextCursor가 처음부터 있어 마운트 이중 페치 없이 더보기/무한 스크롤 동작.
 */
export default async function FeedPage() {
  const feed = await getFeedPage();
  return <FeedView initialFeed={feed} />;
}
