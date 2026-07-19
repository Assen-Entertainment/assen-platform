"use client";
import * as React from "react";
import Link from "next/link";
import { Avatar, Button, Tabs, TabsList, TabsTrigger, TabsContent, EmptyState } from "@/components/ui";
import type { Creator } from "@/lib/api";

function FollowRow({ c }: { c: Creator }) {
  const [following, setFollowing] = React.useState(Boolean(c.following));
  return (
    <div className="flex items-center gap-3 p-3">
      <Link href={`/creator/${c.handle}`} className="flex min-w-0 flex-1 items-center gap-3">
        <Avatar fallback={c.name.slice(0, 1)} size="md" verified={c.verified} />
        <div className="flex min-w-0 flex-col">
          <span className="line-clamp-1 text-label text-on-surface">{c.name}</span>
          <span className="line-clamp-1 text-caption text-on-surface-variant">@{c.handle}</span>
        </div>
      </Link>
      <Button variant={following ? "outline" : "accent"} size="sm" onClick={() => setFollowing((v) => !v)}>
        {following ? "팔로잉" : "팔로우"}
      </Button>
    </div>
  );
}

export function FollowersView({
  creatorName,
  followers,
  following,
}: {
  creatorName: string;
  followers: Creator[];
  following: Creator[];
}) {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <h1 className="text-headline text-on-surface">{creatorName}</h1>
      <Tabs defaultValue="followers">
        <TabsList>
          <TabsTrigger value="followers">팔로워 {followers.length}</TabsTrigger>
          <TabsTrigger value="following">팔로잉 {following.length}</TabsTrigger>
        </TabsList>
        <TabsContent value="followers" className="pt-2">
          {followers.length ? (
            <div className="divide-y divide-outline overflow-hidden rounded-lg border border-outline">
              {followers.map((c) => (
                <FollowRow key={c.id} c={c} />
              ))}
            </div>
          ) : (
            <EmptyState title="아직 팔로워가 없어요" />
          )}
        </TabsContent>
        <TabsContent value="following" className="pt-2">
          {following.length ? (
            <div className="divide-y divide-outline overflow-hidden rounded-lg border border-outline">
              {following.map((c) => (
                <FollowRow key={c.id} c={c} />
              ))}
            </div>
          ) : (
            <EmptyState title="팔로잉이 없어요" />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
