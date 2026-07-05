"use client";
import * as React from "react";
import Link from "next/link";
import {
  Button,
  EmptyState,
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
import { config } from "@/lib/config";
import { useSession } from "@/lib/session";
import { ApiError, apiErrorMessage, type Post } from "@/lib/api";
import { usePosts, useUpdatePost, useDeletePost } from "@/lib/api/queries";

/**
 * Studio 포스트 관리 — 발행한 크리에이터 포스트 목록/수정/삭제(오너 뷰).
 * 목록은 기존 커서 fetcher(getPostsPage?creator_id=)를 재사용한다. 수정=본문·19+ 인라인 시트,
 * 삭제=확인 다이얼로그 → 낙관적 제거(+롤백). 실 API/mock 양쪽 동작(회귀 0).
 */
export default function StudioPostsPage() {
  const { user, mounted } = useSession();
  const live = Boolean(config.apiUrl);
  // 오너(크리에이터) 식별 — 실 경로는 세션 사용자 id, mock 데모는 데모 크리에이터(c1: 별빛 일러스트).
  const creatorId = live ? user?.id : "c1";

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-headline text-on-surface">포스트 관리</h1>
        <Button asChild>
          <Link href="/studio/posts/new">새 포스트</Link>
        </Button>
      </div>

      {live && !mounted ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : creatorId ? (
        <StudioPostsList creatorId={creatorId} />
      ) : (
        <EmptyState
          title="크리에이터 계정이 필요해요"
          description="포스트 관리는 크리에이터 계정에서만 이용할 수 있어요."
        />
      )}
    </div>
  );
}

/** 오너 포스트 목록 — creatorId가 확정된 뒤 마운트(usePosts를 유효 id로만 호출). */
function StudioPostsList({ creatorId }: { creatorId: string }) {
  const { toast } = useToast();
  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } = usePosts(creatorId);
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
