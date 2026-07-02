import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPost, getComments } from "@/lib/api";
import { PostDetailView } from "./post-detail-view";

/** Post 상세 — 동적 라우트(/post/[id]). 서버 fetch → 클라 뷰(initialData 하이드레이션·낙관적 뮤테이션). */
export default async function PostDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const post = await getPost(id);
  if (!post) notFound();
  const comments = await getComments(id);
  return <PostDetailView post={post} comments={comments} />;
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const post = await getPost(id);
  if (!post) return { title: "포스트" };
  const title = `${post.creatorName}의 포스트`;
  return { title, description: post.body?.slice(0, 80), openGraph: { title, description: post.body?.slice(0, 80) } };
}
