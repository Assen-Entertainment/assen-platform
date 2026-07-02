"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { PostCard, EmptyState } from "@/components/ui";
import { useFeed, useToggleLike } from "@/lib/api/queries";
import type { Post } from "@/lib/api";

/** 팔로잉 피드 뷰(클라). 좋아요=낙관적, 카드=포스트 상세 링크. */
export function FeedView({ initialPosts }: { initialPosts: Post[] }) {
  const router = useRouter();
  const { data } = useFeed(initialPosts);
  const toggleLike = useToggleLike();
  const posts = data ?? initialPosts;

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="mb-4 text-headline text-on-surface">팔로잉</h1>
      {posts.length === 0 ? (
        <EmptyState title="아직 피드가 비어 있어요" description="관심 있는 크리에이터를 팔로우해 보세요." />
      ) : (
        <div className="overflow-hidden rounded-lg border border-outline">
          {posts.map((p) => (
            <PostCard
              key={p.id}
              creatorName={p.creatorName}
              creatorMeta={p.creatorMeta}
              verified={p.verified}
              avatarFallback={p.creatorName.slice(0, 1)}
              body={p.body}
              media={
                <Link
                  href={`/post/${p.id}`}
                  aria-label={`${p.creatorName}의 포스트 상세 보기`}
                  className="block aspect-video w-full bg-surface-container-high transition-opacity hover:opacity-90"
                />
              }
              likeCount={p.likeCount}
              commentCount={p.commentCount}
              liked={p.liked}
              onLike={() => toggleLike.mutate({ id: p.id, next: !p.liked })}
              onComment={() => router.push(`/post/${p.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
