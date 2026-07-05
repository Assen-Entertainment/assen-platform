"use client";
import * as React from "react";
import Link from "next/link";
import {
  Button,
  EmptyState,
  ErrorState,
  Spinner,
  Divider,
  Badge,
  Dialog,
  DialogContent,
  DialogClose,
  DialogTitle,
  DialogDescription,
  TextArea,
  Switch,
} from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { ApiError, apiErrorMessage, type Post } from "@/lib/api";
import { useStudioPosts, useUpdatePost, useDeletePost } from "@/lib/api/queries";

/**
 * Studio 포스트 관리 — 발행한 크리에이터 포스트 목록/수정/삭제(오너 뷰).
 * 목록은 오너 스코프 fetcher(GET /studio/posts)를 소비한다(소비자 게이트 미적용 → 오너의 19+·draft도
 * 노출). 수정=본문·19+ 인라인 시트, 삭제=확인 다이얼로그 → 낙관적 제거(+롤백). 실 API/mock 양쪽 동작.
 */
export default function StudioPostsPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-headline text-on-surface">포스트 관리</h1>
        <Button asChild>
          <Link href="/studio/posts/new">새 포스트</Link>
        </Button>
      </div>

      <StudioPostsList />
    </div>
  );
}

/** 오너 포스트 목록 — GET /studio/posts 소비(오너 스코프). 403(비크리에이터)·401(세션 만료)은 방어 안내. */
function StudioPostsList() {
  const { toast } = useToast();
  const { data, isLoading, isError, error, refetch, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useStudioPosts();
  const updatePost = useUpdatePost();
  const deletePost = useDeletePost();
  const posts = data ?? [];

  const [editing, setEditing] = React.useState<Post | null>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<Post | null>(null);

  // 실패 토스트 — 401은 전역 세션 가드가 처리하므로 무시, 그 외는 error code(apiErrorMessage).
  const onError = (e: unknown, fallback: string) => {
    if (e instanceof ApiError && e.status === 401) return;
    toast({ title: fallback, description: apiErrorMessage(e) });
  };

  const onConfirmDelete = () => {
    if (!deleteTarget) return;
    deletePost.mutate(deleteTarget.id, {
      onSuccess: () => toast({ title: "포스트를 삭제했어요", description: "목록에서 제거되었습니다." }),
      onError: (e) => onError(e, "삭제하지 못했어요"),
    });
    setDeleteTarget(null);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner />
      </div>
    );
  }

  // 403(OwnerRequired) — 오너 스코프 엔드포인트가 비크리에이터를 거부. 방어 안내(빈 목록과 구분).
  if (isError && error instanceof ApiError && error.status === 403) {
    return (
      <EmptyState
        title="크리에이터 계정이 필요해요"
        description="포스트 관리는 크리에이터 계정에서만 이용할 수 있어요."
      />
    );
  }
  // 401(세션 만료/무효) — client.ts refresh-retry 실패 후 도달(회복 불가 세션). getStudioPostsPage가
  // 이 401을 빈 페이지로 삼키지 않고 전파하므로, "발행 포스트 없음"으로 오표시하지 않고 재로그인 안내.
  if (isError && error instanceof ApiError && error.status === 401) {
    return (
      <EmptyState
        title="다시 로그인해 주세요"
        description="세션이 만료되었어요. 다시 로그인하면 포스트 관리를 이어갈 수 있어요."
        action={
          <Button asChild>
            <Link href="/login?next=/studio/posts">로그인</Link>
          </Button>
        }
      />
    );
  }
  // 그 외 오류(네트워크 등) — 재시도 안내(401·403은 위에서 방어 안내로 분기).
  if (isError) {
    return (
      <div className="flex justify-center py-16">
        <ErrorState onRetry={() => refetch()} />
      </div>
    );
  }

  if (posts.length === 0) {
    return (
      <EmptyState
        title="아직 발행한 포스트가 없어요"
        description="첫 포스트를 작성해 팬들에게 소식을 전해보세요."
        action={
          <Button asChild>
            <Link href="/studio/posts/new">새 포스트 작성</Link>
          </Button>
        }
      />
    );
  }

  return (
    <>
      <div className="overflow-hidden rounded-lg border border-outline">
        {posts.map((p, i) => (
          <div key={p.id}>
            {i > 0 ? <Divider /> : null}
            <div className="flex items-start justify-between gap-3 p-4">
              <div className="flex min-w-0 flex-col gap-1">
                <p className="line-clamp-2 text-body-m text-on-surface">
                  {p.body?.replace(/\s*\n+\s*/g, " ").trim() || "(본문 없음)"}
                </p>
                <span className="flex items-center gap-2 text-caption text-on-surface-variant">
                  <span>
                    좋아요 {p.likeCount.toLocaleString("ko-KR")} · 댓글 {p.commentCount.toLocaleString("ko-KR")}
                  </span>
                  {p.isAdult ? <Badge variant="warning">19+</Badge> : null}
                </span>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button variant="outline" size="sm" onClick={() => setEditing(p)}>
                  수정
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="border-error text-error hover:bg-error-container"
                  onClick={() => setDeleteTarget(p)}
                >
                  삭제
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 더 불러오기 — 커서 다음 페이지가 있을 때만(관리 화면은 버튼 페이지네이션). */}
      {hasNextPage ? (
        <div className="flex justify-center">
          <Button variant="outline" onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
            {isFetchingNextPage ? "불러오는 중…" : "더 불러오기"}
          </Button>
        </div>
      ) : null}

      {/* 수정 시트 — 본문·19+ 플래그(발행 폼과 동일 필드) → PATCH /posts/{id}. */}
      {editing ? (
        <PostEditDialog
          key={editing.id}
          post={editing}
          saving={updatePost.isPending}
          onClose={() => setEditing(null)}
          onSave={(patch) =>
            updatePost.mutate(
              { id: editing.id, ...patch },
              {
                onSuccess: () => {
                  toast({ title: "포스트를 수정했어요", description: "변경 사항이 저장되었습니다." });
                  setEditing(null);
                },
                onError: (e) => onError(e, "수정하지 못했어요"),
              },
            )
          }
        />
      ) : null}

      {/* 삭제 확인 — 파괴적 액션. */}
      <Dialog open={deleteTarget !== null} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <DialogContent>
          <DialogTitle>포스트를 삭제할까요?</DialogTitle>
          <DialogDescription>
            삭제하면 이 포스트가 피드와 프로필에서 사라지고 되돌릴 수 없어요.
          </DialogDescription>
          <div className="mt-1 flex gap-2">
            <DialogClose asChild>
              <Button variant="outline" className="flex-1">
                취소
              </Button>
            </DialogClose>
            <Button
              className="flex-1 bg-error text-on-error hover:opacity-90"
              onClick={onConfirmDelete}
              disabled={deletePost.isPending}
            >
              삭제하기
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

/** 포스트 편집 시트 — 본문 + 19+ 등급(발행 폼 재사용). 로컬 상태 → PATCH. */
function PostEditDialog({
  post,
  saving,
  onSave,
  onClose,
}: {
  post: Post;
  saving: boolean;
  onSave: (patch: { body: string; isAdult: boolean }) => void;
  onClose: () => void;
}) {
  const [body, setBody] = React.useState(post.body ?? "");
  const [adult, setAdult] = React.useState(Boolean(post.isAdult));
  const submit = () => onSave({ body: body.trim(), isAdult: adult });

  return (
    <Dialog open onOpenChange={(o) => (!o ? onClose() : undefined)}>
      <DialogContent>
        <DialogTitle>포스트 수정</DialogTitle>
        <DialogDescription>본문과 19+ 등급을 수정할 수 있어요.</DialogDescription>
        <TextArea
          label="본문"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          maxLength={2000}
          showCount
          className="min-h-40"
        />
        <div className="flex items-start justify-between gap-3 rounded-md border border-outline bg-surface p-4">
          <div className="flex min-w-0 flex-col gap-0.5">
            <span className="text-label text-on-surface">19+ 성인 콘텐츠</span>
            <span className="text-caption text-on-surface-variant">
              켜면 성인 등급으로 표시돼요. 노출은 서버 정책에 따라 인증 이용자에게만 허용됩니다.
            </span>
          </div>
          <Switch aria-label="19세 이상 성인 콘텐츠" checked={adult} onCheckedChange={setAdult} />
        </div>
        <div className="mt-1 flex gap-2">
          <DialogClose asChild>
            <Button variant="outline" className="flex-1">
              취소
            </Button>
          </DialogClose>
          <Button className="flex-1" onClick={submit} disabled={saving || body.trim().length === 0}>
            저장
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
