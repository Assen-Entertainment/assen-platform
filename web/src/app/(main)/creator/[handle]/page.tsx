import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getCreator, getPostsPage, getProducts, getMembershipTiers } from "@/lib/api";
import { config } from "@/lib/config";
import { JsonLd } from "@/components/json-ld";
import { CreatorProfileView } from "./creator-profile-view";

/** Creator 프로필 — 동적 라우트(/creator/[handle]). 서버 fetch → 클라 뷰(initialData 하이드레이션). */
export default async function CreatorPage({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  const creator = await getCreator(handle);
  if (!creator) notFound();
  // 포스트는 커서 Page 시드(무한 로드 이중 페치 제거), 스토어·티어는 단순 목록.
  const [posts, products, tiers] = await Promise.all([
    getPostsPage(creator.id),
    getProducts(creator.id),
    getMembershipTiers(creator.id),
  ]);
  // ProfilePage JSON-LD(#5a) — 실 데이터만(이름·핸들·소개·팔로워). 평점/리뷰 등 미보유 필드는 날조하지 않는다.
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ProfilePage",
    mainEntity: {
      "@type": "Person",
      name: creator.name,
      alternateName: `@${creator.handle}`,
      url: `${config.siteUrl}/creator/${creator.handle}`,
      ...(creator.bio ? { description: creator.bio } : {}),
      ...(creator.avatarUrl ? { image: creator.avatarUrl } : {}),
      interactionStatistic: {
        "@type": "InteractionCounter",
        interactionType: "https://schema.org/FollowAction",
        userInteractionCount: creator.followers,
      },
    },
  };
  return (
    <>
      <JsonLd data={jsonLd} />
      <CreatorProfileView creator={creator} posts={posts} products={products} tiers={tiers} />
    </>
  );
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
    alternates: { canonical: `/creator/${creator.handle}` },
    openGraph: { title: creator.name, description, type: "profile" },
  };
}
