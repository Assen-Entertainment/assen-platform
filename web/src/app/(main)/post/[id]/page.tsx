import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPost, getCommentsPage } from "@/lib/api";
import { PostDetailView } from "./post-detail-view";

/** Post 상세 — 동적 라우트(/post/[id]). 서버 fetch → 클라 뷰(initialData 하이드레이션·낙관적 뮤테이션). */
export default async function PostDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const post = await getPost(id);
  if (!post) notFound();
  // 댓글은 커서 Page 시드(무한 로드 이중 페치 제거).
  const comments = await getCommentsPage(id);
  return <PostDetailView post={post} comments={comments} />;
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const post = await getPost(id);
  if (!post) return { title: "포스트" };
  const title = `${post.creatorName}의 포스트`;
  return { title, description: post.body?.slice(0, 80), openGraph: { title, description: post.body?.slice(0, 80) } };
}
