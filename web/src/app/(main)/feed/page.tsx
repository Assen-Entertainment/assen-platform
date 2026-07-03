import type { Metadata } from "next";
import { getPosts } from "@/lib/api";
import { FeedView } from "./feed-view";

export const metadata: Metadata = {
  title: "피드",
  description: "팔로우한 크리에이터의 최신 포스트를 한곳에서 확인하세요.",
};

/** Feed — 팔로잉 피드. 서버 fetch → 클라 뷰(initialData 하이드레이션·낙관적 좋아요). */
export default async function FeedPage() {
  const posts = await getPosts();
  return <FeedView initialPosts={posts} />;
}
