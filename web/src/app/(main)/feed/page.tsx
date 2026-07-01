import { getPosts } from "@/lib/api";
import { FeedView } from "./feed-view";

/** Feed — 팔로잉 피드. 서버 fetch → 클라 뷰(initialData 하이드레이션·낙관적 좋아요). */
export default async function FeedPage() {
  const posts = await getPosts();
  return <FeedView initialPosts={posts} />;
}
