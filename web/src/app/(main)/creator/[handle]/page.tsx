import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getCreator, getPosts, getProducts, getMembershipTiers } from "@/lib/api";
import { CreatorProfileView } from "./creator-profile-view";

/** Creator 프로필 — 동적 라우트(/creator/[handle]). 서버 fetch → 클라 뷰(initialData 하이드레이션). */
export default async function CreatorPage({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  const creator = await getCreator(handle);
  if (!creator) notFound();
  const [posts, products, tiers] = await Promise.all([
    getPosts(creator.id),
    getProducts(creator.id),
    getMembershipTiers(creator.id),
  ]);
  return <CreatorProfileView creator={creator} posts={posts} products={products} tiers={tiers} />;
}

/** OG 메타 — 공유 핵심(크리에이터별 고유 제목·설명). */
export async function generateMetadata({ params }: { params: Promise<{ handle: string }> }): Promise<Metadata> {
  const { handle } = await params;
  const creator = await getCreator(handle);
  if (!creator) return { title: "크리에이터" };
  const description =
    creator.bio ?? `@${creator.handle} · 팔로워 ${creator.followers.toLocaleString("ko-KR")}`;
  return {
    title: creator.name,
    description,
    openGraph: { title: creator.name, description, type: "profile" },
  };
}
