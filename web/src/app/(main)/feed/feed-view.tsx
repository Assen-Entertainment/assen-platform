"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  PostCard,
  Button,
  EmptyState,
  ErrorState,
  ReportSheet,
  LockedOverlay,
  Sheet,
  SheetContent,
  SheetTitle,
  Dialog,
  DialogContent,
  DialogClose,
  DialogTitle,
  DialogDescription,
} from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { gradientStyle } from "@/lib/placeholder";
import { useSession } from "@/lib/session";
import { useFeed, useToggleLike, useReport, useBlockCreator } from "@/lib/api/queries";
import { ApiError, apiErrorMessage, type Post } from "@/lib/api";

/** 팔로잉 피드 뷰(클라). 좋아요=낙관적, 공유=클립보드, 더보기=신고 등 액션. */
export function FeedView({ initialPosts }: { initialPosts: Post[] }) {
  const router = useRouter();
  const { toast } = useToast();
  const { user, mounted } = useSession();
  const adultVerified = user?.adultVerified === true;
  const { data, isError, refetch, fetchNextPage, hasNextPage, isFetchingNextPage } = useFeed(initialPosts);
  const toggleLike = useToggleLike();
  const report = useReport();
  const blockCreator = useBlockCreator();
  const posts = data ?? initialPosts;

  // 더보기 액션 메뉴 대상 / 신고 시트 대상 포스트 id / 차단 확인 대상(크리에이터).
  const [menuPostId, setMenuPostId] = React.useState<string | null>(null);
  const [reportPostId, setReportPostId] = React.useState<string | null>(null);
  const [blockTarget, setBlockTarget] = React.useState<{ creatorId: string; creatorName: string } | null>(null);

  // 차단 확정 — 낙관적 필터로 피드에서 해당 크리에이터 포스트 즉시 사라짐(+자동 언팔). 401은 세션 가드.
  const onConfirmBlock = () => {
    if (!blockTarget) return;
    const { creatorId, creatorName } = blockTarget;
    blockCreator.mutate(
      { creatorId },
      {
        onSuccess: () =>
          toast({ title: "차단했어요", description: `${creatorName}님의 포스트가 더 이상 보이지 않아요.` }),
        onError: (e) => {
          if (e instanceof ApiError && e.status === 401) return;
          toast({ title: "차단하지 못했어요", description: apiErrorMessage(e) });
        },
      },
    );
    setBlockTarget(null);
  };

  const postUrl = (id: string) =>
    typeof window !== "undefined" ? `${window.location.origin}/post/${id}` : `/post/${id}`;

  const share = async (id: string) => {
    const url = postUrl(id);
    try {
      await navigator.clipboard.writeText(url);
      toast({ title: "링크를 복사했어요", description: "원하는 곳에 붙여넣어 공유하세요." });
    } catch {
      // 클립보드 접근 불가 — 안내 토스트로 대체.
      toast({ title: "복사하지 못했어요", description: url });
    }
  };

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="mb-4 text-headline text-on-surface">팔로잉</h1>
      {isError && !data ? (
        <ErrorState onRetry={() => refetch()} />
      ) : posts.length === 0 ? (
        <EmptyState title="아직 피드가 비어 있어요" description="관심 있는 크리에이터를 팔로우해 보세요." />
      ) : (
        <>
        <div className="overflow-hidden rounded-lg border border-outline">
          {posts.map((p) => (
            <PostCard
              key={p.id}
              creatorName={p.creatorName}
              creatorMeta={p.creatorMeta}
              verified={p.verified}
              avatarFallback={p.creatorName.slice(0, 1)}
              avatarTone={p.creatorId}
              body={p.body}
              media={
                // 세션 복원 전(mounted=false)엔 게이트 판정 보류 — 인증 뷰어에게 블러→언블러 플래시 방지
                // (서버가 이미 미인증 뷰어에게 adult를 미반환하므로 실누출 0, 순수 시각 개선).
                mounted && p.isAdult && !adultVerified ? (
                  // 19+ 성인 콘텐츠 방어 게이트 — 서버가 이미 미인증 뷰어에게 숨기지만 UI도 블러 처리.
                  // 링크 대신 성인 인증 CTA(/age-gate)로 유도(포스트로 새지 않도록 비링크).
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
                ) : p.locked ? (
                  // 잠긴 콘텐츠 — 프로필과 동일하게 seed 그라디언트 + 블러 LockedOverlay.
                  // 링크는 기존대로 /post/[id] 유지(중첩 인터랙티브 방지 위해 CTA 없이 전체 링크).
                  <Link
                    href={`/post/${p.id}`}
                    aria-label={`${p.creatorName}의 멤버십 전용 포스트`}
                    className="block"
                  >
                    <div className="relative aspect-video w-full" style={gradientStyle(p.id)}>
                      <LockedOverlay title="멤버십 전용" description="멤버십에 가입하면 볼 수 있어요." />
                    </div>
                  </Link>
                ) : (
                  <Link
                    href={`/post/${p.id}`}
                    aria-label={`${p.creatorName}의 포스트 상세 보기`}
                    className="block"
                  >
                    <div
                      className="aspect-video w-full transition-opacity hover:opacity-90"
                      style={gradientStyle(p.id)}
                    />
                  </Link>
                )
              }
              likeCount={p.likeCount}
              commentCount={p.commentCount}
              liked={p.liked}
              onLike={() => toggleLike.mutate({ id: p.id, next: !p.liked })}
              onComment={() => router.push(`/post/${p.id}`)}
              onShare={() => share(p.id)}
              onMore={() => setMenuPostId(p.id)}
            />
          ))}
        </div>
        {/* 더보기 — 커서 다음 페이지가 있을 때만 노출(무한 쿼리 fetchNextPage). */}
        {hasNextPage ? (
          <div className="mt-4 flex justify-center">
            <Button variant="outline" onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
              {isFetchingNextPage ? "불러오는 중…" : "더보기"}
            </Button>
          </div>
        ) : null}
        </>
      )}

      {/* 더보기 액션 메뉴(bottom sheet). */}
      <Sheet open={menuPostId !== null} onOpenChange={(o) => !o && setMenuPostId(null)}>
        <SheetContent side="bottom" className="sm:mx-auto sm:max-w-md">
          <SheetTitle className="sr-only">포스트 더보기</SheetTitle>
          <div className="flex flex-col">
            <button
              type="button"
              className="rounded-md px-3 py-3 text-left text-body-m text-on-surface transition-colors hover:bg-surface-container-high"
              onClick={() => {
                if (menuPostId) share(menuPostId);
                setMenuPostId(null);
              }}
            >
              링크 복사
            </button>
            <button
              type="button"
              className="rounded-md px-3 py-3 text-left text-body-m text-on-surface transition-colors hover:bg-surface-container-high"
              onClick={() => {
                const post = posts.find((p) => p.id === menuPostId);
                if (post) setBlockTarget({ creatorId: post.creatorId, creatorName: post.creatorName });
                setMenuPostId(null);
              }}
            >
              이 크리에이터 차단
            </button>
            <button
              type="button"
              className="rounded-md px-3 py-3 text-left text-body-m text-error transition-colors hover:bg-surface-container-high"
              onClick={() => {
                setReportPostId(menuPostId);
                setMenuPostId(null);
              }}
            >
              신고하기
            </button>
          </div>
        </SheetContent>
      </Sheet>

      {/* 차단 확인 — 파괴적 UX(자동 언팔로우 안내). 기존 Dialog 패턴 재사용. */}
      <Dialog open={blockTarget !== null} onOpenChange={(o) => !o && setBlockTarget(null)}>
        <DialogContent>
          <DialogTitle>
            {blockTarget ? `${blockTarget.creatorName}님을 차단할까요?` : "이 크리에이터를 차단할까요?"}
          </DialogTitle>
          <DialogDescription>
            차단하면 이 크리에이터의 포스트가 피드에서 사라지고, 팔로우가 자동으로 해제돼요. 설정 &gt;
            차단 목록에서 언제든 해제할 수 있어요.
          </DialogDescription>
          <div className="mt-1 flex gap-2">
            <DialogClose asChild>
              <Button variant="outline" className="flex-1">
                취소
              </Button>
            </DialogClose>
            <Button
              className="flex-1 bg-error text-on-error hover:opacity-90"
              onClick={onConfirmBlock}
              disabled={blockCreator.isPending}
            >
              차단하기
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* 신고 시트. USE_API면 /safety/fan-reports 실 접수, 아니면 mock(sleep). */}
      <ReportSheet
        open={reportPostId !== null}
        onOpenChange={(o) => !o && setReportPostId(null)}
        onSubmit={(payload) => {
          report.mutate(
            { reportType: payload.reason, narrative: payload.detail || undefined },
            {
              onSuccess: () =>
                toast({ title: "신고가 접수되었어요", description: "운영팀이 검토 후 조치할게요." }),
              onError: (e) => {
                // 401은 전역 세션 가드가 처리 → 그 외 오류만 안내.
                if (!(e instanceof ApiError && e.status === 401)) {
                  toast({ title: "신고를 접수하지 못했어요", description: "잠시 후 다시 시도해 주세요." });
                }
              },
            },
          );
          setReportPostId(null);
        }}
      />
    </div>
  );
}
