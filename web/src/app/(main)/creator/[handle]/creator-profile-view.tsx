"use client";
import * as React from "react";
import {
  Avatar, Button, Tabs, TabsList, TabsTrigger, TabsContent, PostCard, MonetizableItem, MembershipTierCard,
} from "@/components/ui";
import { creatorAccentVars } from "@/lib/creator-accent";
import { useCreator, useToggleFollow } from "@/lib/api/queries";
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
  const [tab, setTab] = React.useState("posts");
  const { data } = useCreator(creator.handle, creator);
  const c = data ?? creator;
  const follow = useToggleFollow(creator.handle);
  const accent = c.accentColor;
  const initial = c.name.slice(0, 1);

  return (
    <div style={accent ? creatorAccentVars(accent) : undefined} className="mx-auto flex max-w-4xl flex-col">
      <div className="h-44 w-full rounded-lg" style={accent ? { backgroundColor: "var(--creator-accent)" } : { backgroundImage: "var(--gradient-brand)" }} />

      <div className="-mt-10 flex items-end gap-4 px-2">
        <Avatar fallback={initial} size="xl" verified={c.verified} className="ring-4 ring-surface" />
        <div className="flex flex-1 flex-wrap items-center justify-between gap-3 pb-2">
          <div>
            <h1 className="text-headline text-on-surface">{c.name}</h1>
            <p className="text-body-s text-on-surface-variant">
              @{c.handle} · 팔로워 {c.followers.toLocaleString("ko-KR")}
              {c.posts ? ` · 포스트 ${c.posts}` : ""}
            </p>
          </div>
          <div className="flex gap-2">
            {/* 메시지/DM CTA는 실시간 챗(B6·게이트) 구현 전까지 제외 — 동작 없는 버튼 미노출. */}
            <Button
              variant={c.following ? "outline" : "accent"}
              disabled={follow.isPending}
              onClick={() => follow.mutate(!c.following)}
            >
              {c.following ? "팔로잉" : "팔로우"}
            </Button>
          </div>
        </div>
      </div>

      {c.bio ? <p className="px-2 py-4 text-body-m text-on-surface">{c.bio}</p> : null}

      <Tabs value={tab} onValueChange={setTab} className="px-2">
        <TabsList>
          <TabsTrigger value="posts">포스트</TabsTrigger>
          <TabsTrigger value="store">스토어</TabsTrigger>
          <TabsTrigger value="membership">멤버십</TabsTrigger>
        </TabsList>

        <TabsContent value="posts" className="pt-2">
          <div className="overflow-hidden rounded-lg border border-outline">
            {posts.map((p) => (
              <PostCard
                key={p.id}
                creatorName={p.creatorName}
                creatorMeta={p.creatorMeta}
                verified={p.verified}
                avatarFallback={initial}
                body={p.body}
                media={<div className="aspect-video w-full bg-surface-container-high" />}
                likeCount={p.likeCount}
                commentCount={p.commentCount}
                liked={p.liked}
              />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="store" className="pt-4">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            {products.map((p) => (
              <MonetizableItem key={p.id} type={p.type} title={p.title} price={`₩${p.price.toLocaleString("ko-KR")}`} meta={p.meta} />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="membership" className="pt-4">
          <div className="grid gap-4 sm:grid-cols-3">
            {tiers.map((t) => (
              <MembershipTierCard key={t.id} name={t.name} price={t.price} period={t.period} benefits={t.benefits} badge={t.badge} featured={t.featured} accent={t.featured} />
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
