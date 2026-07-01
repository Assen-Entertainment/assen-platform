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
    getProducts(),
    getMembershipTiers(creator.id),
  ]);
  return <CreatorProfileView creator={creator} posts={posts} products={products} tiers={tiers} />;
}
