"use client";
import * as React from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { PostCard, TextArea, Button, Avatar, LockedOverlay } from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { gradientStyle } from "@/lib/placeholder";
import { useSession } from "@/lib/session";
import { usePost, useComments, useToggleLike, useAddComment } from "@/lib/api/queries";
import type { Post, Comment, Page } from "@/lib/api";

// 라이트박스 코드 스플리팅(R5-W3 #7b) — 열릴 때만 로드. document 접근 → ssr:false.
const MediaViewer = dynamic(() => import("@/components/ui/media-viewer").then((m) => m.MediaViewer), {
  ssr: false,
});

/** Post 상세 뷰(클라). 좋아요·댓글=낙관적 뮤테이션, 공유=토스트. */
export function PostDetailView({ post: initialPost, comments: initialComments }: { post: Post; comments: Page<Comment> }) {
  const { data: post } = usePost(initialPost.id, initialPost);
  const {
    data: comments,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useComments(initialPost.id, initialComments);
  const toggleLike = useToggleLike();
  const addComment = useAddComment(initialPost.id);
  const { toast } = useToast();
  const { user, mounted } = useSession();
  const adultVerified = user?.adultVerified === true;
  const [text, setText] = React.useState("");
  const [viewerOpen, setViewerOpen] = React.useState(false);

  const p = post ?? initialPost;
  const list = comments ?? initialComments.items;
  // 19+ 방어 게이트 — 서버가 미인증 뷰어에게 이미 숨기지만, 도달 시 미디어를 블러 처리.
  // 세션 복원 전(mounted=false)엔 판정 보류 — 인증 뷰어에게 블러→언블러 플래시 방지(실누출 0, 시각 개선).
  const adultBlocked = mounted && Boolean(p.isAdult) && !adultVerified;

  const onShare = () => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href).catch(() => {});
    }
    toast({ title: "링크가 복사됐어요", description: "포스트 링크를 클립보드에 복사했습니다." });
  };

  const doSubmit = () => {
    const body = text.trim();
    if (!body || addComment.isPending) return;
    addComment.mutate(body);
    setText("");
  };
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    doSubmit();
  };
  // ⌘/Ctrl+Enter로 빠른 등록(멀티라인 입력 중에도) — 일반 Enter는 줄바꿈.
  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      doSubmit();
    }
  };

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-5">
      <div className="overflow-hidden rounded-lg border border-outline">
        <PostCard
          creatorName={p.creatorName}
          creatorMeta={p.creatorMeta}
          verified={p.verified}
          avatarFallback={p.creatorName.slice(0, 1)}
          avatarTone={p.creatorId}
          body={p.body}
          media={
            adultBlocked ? (
              <div className="relative aspect-video w-full" style={gradientStyle(p.id)}>
                <LockedOverlay
                  title="성인(19+) 콘텐츠"
                  description="본인인증 후 볼 수 있어요."
                  cta={
                    <Button size="sm" asChild>
                      <Link href="/age-gate">성인 인증하기</Link>
                    </Button>
                  }
                />
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setViewerOpen(true)}
                aria-label="미디어 크게 보기"
                className="block aspect-video w-full transition-opacity hover:opacity-95"
                style={gradientStyle(p.id)}
              />
            )
          }
          likeCount={p.likeCount}
          commentCount={p.commentCount}
          liked={p.liked}
          onLike={() => toggleLike.mutate({ id: p.id, next: !p.liked })}
          onShare={onShare}
        />
      </div>

      <MediaViewer
        open={viewerOpen}
        onClose={() => setViewerOpen(false)}
        seed={p.id}
        alt={`${p.creatorName}의 포스트 미디어`}
        caption={p.body}
      />

      <h2 className="text-title-m text-on-surface">댓글 {p.commentCount}</h2>
      <ul className="flex flex-col gap-4">
        {list.length === 0 ? (
          <li className="text-body-s text-on-surface-variant">첫 댓글을 남겨보세요.</li>
        ) : (
          list.map((c) => (
            <li key={c.id} className="flex gap-2">
              <Avatar fallback={c.authorFallback ?? c.author.slice(0, 1)} size="sm" />
              <div className="flex min-w-0 flex-col">
                <span className="text-label text-on-surface">
                  {c.author} <span className="text-caption font-normal text-on-surface-variant">· {c.createdAt}</span>
                </span>
                <span className="text-body-s text-on-surface-variant">{c.body}</span>
              </div>
            </li>
          ))
        )}
      </ul>

      {/* 더보기 — 댓글 커서 다음 페이지가 있을 때만(무한 쿼리). */}
      {hasNextPage ? (
        <div className="flex justify-center">
          <Button variant="outline" onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
            {isFetchingNextPage ? "불러오는 중…" : "댓글 더보기"}
          </Button>
        </div>
      ) : null}

      {/* 댓글 작성(#3) — 멀티라인 여유(min-height·전체 폭)를 준 TextArea 컴포저. */}
      <form onSubmit={submit} className="flex flex-col gap-2">
        <TextArea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="따뜻한 댓글을 남겨보세요"
          aria-label="댓글 입력"
          rows={3}
          maxLength={500}
          showCount
          className="min-h-24 resize-y"
        />
        <div className="flex items-center justify-between gap-2">
          <span className="text-caption text-on-surface-variant">⌘·Ctrl+Enter로 빠르게 등록</span>
          <Button type="submit" disabled={!text.trim() || addComment.isPending}>
            등록
          </Button>
        </div>
      </form>
    </div>
  );
}
