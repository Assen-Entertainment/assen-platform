"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Button,
  Tabs, TabsList, TabsTrigger, TabsContent,
  PostCard, MonetizableItem, MembershipTierCard, ErrorState, EmptyState,
  CreatorHomeHeader, GiftSheet, LockedOverlay,
} from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { creatorAccentVars } from "@/lib/creator-accent";
import { gradientStyle } from "@/lib/placeholder";
import { useCreator, useToggleFollow, usePosts, useToggleLike } from "@/lib/api/queries";
import type { Creator, Post, Product, MembershipTier } from "@/lib/api";

/** CreatorProfile 뷰 — 동적 + React Query. 팔로우=낙관적 뮤테이션(캐시 즉시 반영). */
export function CreatorProfileView({
  creator,
  posts,
  products,
  tiers,
}: {
  creator: Creator;
  posts: Post[];
  products: Product[];
  tiers: MembershipTier[];
}) {
  const router = useRouter();
  const { toast } = useToast();
  const [tab, setTab] = React.useState("posts");
  const [giftOpen, setGiftOpen] = React.useState(false);
  const { data, isError, refetch } = useCreator(creator.handle, creator);
  const c = data ?? creator;
  const follow = useToggleFollow(creator.handle);
  const accent = c.accentColor;
  const initial = c.name.slice(0, 1);

  // 포스트 좋아요 — 공용 useToggleLike(캐시 통일). 프로필 포스트도 ["posts", creatorId]
  // 캐시로 하이드레이트 → 뮤테이션이 즉시 UI에 반영되고 피드·상세와 동일 경로.
  const { data: postData } = usePosts(creator.id, posts);
  const postList = postData ?? posts;
  const toggleLike = useToggleLike();

  const share = async (id: string) => {
    const url = `${window.location.origin}/post/${id}`;
    try {
      await navigator.clipboard.writeText(url);
      toast({ title: "링크를 복사했어요", description: url });
    } catch {
      toast({ title: "링크 복사에 실패했어요" });
    }
  };

  if (isError && !data) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <ErrorState onRetry={() => refetch()} />
      </div>
    );
  }

  // 이번 달 목표(placeholder) — 다음 5k 팔로워 구간을 목표로 ProgressBar 소비(#10).
  const goalMax = Math.max(5000, Math.ceil((c.followers + 1) / 5000) * 5000);

  return (
    <div style={accent ? creatorAccentVars(accent) : undefined} className="mx-auto flex max-w-4xl flex-col gap-2">
      <CreatorHomeHeader
        name={c.name}
        handle={c.handle}
        initial={initial}
        followers={c.followers}
        posts={c.posts}
        verified={c.verified}
        bio={c.bio}
        accent={Boolean(accent)}
        following={c.following}
        followPending={follow.isPending}
        onToggleFollow={() => follow.mutate(!c.following)}
        onGift={() => setGiftOpen(true)}
        followersHref={`/creator/${c.handle}/followers`}
        goal={{ label: "이번 달 팔로워 목표", value: c.followers, max: goalMax }}
      />

      <Tabs value={tab} onValueChange={setTab} className="px-2">
        <TabsList>
          <TabsTrigger value="posts">포스트</TabsTrigger>
          <TabsTrigger value="store">스토어</TabsTrigger>
          <TabsTrigger value="membership">멤버십</TabsTrigger>
        </TabsList>

        <TabsContent value="posts" className="pt-2">
          <div className="overflow-hidden rounded-lg border border-outline">
            {postList.map((p) => (
              <PostCard
                key={p.id}
                creatorName={p.creatorName}
                creatorMeta={p.creatorMeta}
                verified={p.verified}
                avatarFallback={initial}
                avatarTone={c.handle}
                body={p.body}
                media={
                  p.locked ? (
                    // 잠긴 콘텐츠(루브릭 #16) — 블러 + 락 + 해제 CTA(→ 멤버십 탭).
                    <div className="relative aspect-video w-full" style={gradientStyle(p.id)}>
                      <LockedOverlay
                        description="멤버십에 가입하면 이 포스트를 볼 수 있어요."
                        cta={
                          <Button size="sm" variant="accent" onClick={() => setTab("membership")}>
                            멤버십 보기
                          </Button>
                        }
                      />
                    </div>
                  ) : (
                    <Link href={`/post/${p.id}`} aria-label="포스트 상세 보기">
                      <div className="aspect-video w-full" style={gradientStyle(p.id)} />
                    </Link>
                  )
                }
                likeCount={p.likeCount}
                commentCount={p.commentCount}
                liked={p.liked}
                onLike={() => toggleLike.mutate({ id: p.id, next: !p.liked })}
                onComment={() => router.push(`/post/${p.id}`)}
                onShare={() => share(p.id)}
              />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="store" className="pt-4">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            {products.map((p) => (
              <MonetizableItem
                key={p.id}
                type={p.type}
                title={p.title}
                price={`₩${p.price.toLocaleString("ko-KR")}`}
                meta={p.meta}
                onAction={() => router.push(`/store/${p.id}`)}
              />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="membership" className="pt-4">
          {tiers.length === 0 ? (
            <EmptyState
              title="아직 멤버십이 없어요"
              description="이 크리에이터는 아직 멤버십을 열지 않았어요. 포스트·스토어를 먼저 둘러보세요."
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-3">
              {tiers.map((t, i) => (
                <MembershipTierCard
                  key={t.id}
                  name={t.name}
                  price={t.price}
                  period={t.period}
                  benefits={t.benefits}
                  badge={t.badge}
                  featured={t.featured}
                  accent={t.featured}
                  inheritNote={i > 0 ? `${tiers[i - 1].name} 혜택 포함` : undefined}
                  onSubscribe={() => router.push(`/checkout?tier=${encodeURIComponent(t.id)}&creator=${encodeURIComponent(c.handle)}`)}
                />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      <GiftSheet open={giftOpen} onOpenChange={setGiftOpen} creatorName={c.name} />
    </div>
  );
}
