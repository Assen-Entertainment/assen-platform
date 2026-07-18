"use client";
import Link from "next/link";
import { Avatar, Button, Card, Divider, EmptyState, ErrorState, Spinner } from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { ApiError, apiErrorMessage } from "@/lib/api";
import { useBlocks, useUnblockCreator } from "@/lib/api/queries";

/**
 * 설정 > 차단 목록 — 내가 차단한 크리에이터 목록 + 개별 "차단 해제"(useUnblockCreator, 낙관적 제거).
 * 차단/해제는 크리에이터 프로필·피드 더보기에서 수행하고, 여기서는 전체 목록을 관리한다.
 */
export default function BlockedSettingsPage() {
  const { toast } = useToast();
  const { data, isLoading, isError, refetch } = useBlocks();
  const unblock = useUnblockCreator();
  const blocks = data ?? [];

  const onUnblock = (creatorId: string, handle: string, name: string) => {
    unblock.mutate(
      { creatorId, handle },
      {
        onSuccess: () =>
          toast({ title: "차단을 해제했어요", description: `${name}님의 콘텐츠를 다시 볼 수 있어요.` }),
        onError: (e) => {
          // 401은 전역 세션 가드가 처리 → 그 외만 안내.
          if (e instanceof ApiError && e.status === 401) return;
          toast({ title: "해제하지 못했어요", description: apiErrorMessage(e) });
        },
      },
    );
  };

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5">
      <h1 className="text-headline text-on-surface">차단 목록</h1>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : isError ? (
        // 로드 실패(비401) — 빈 목록으로 오인 표시하지 않고 에러+재시도. 401은 전역 세션 가드가 처리.
        <Card>
          <ErrorState
            title="목록을 불러오지 못했어요"
            description="차단 목록을 불러오는 중 문제가 생겼어요. 잠시 후 다시 시도해 주세요."
            onRetry={() => refetch()}
          />
        </Card>
      ) : blocks.length === 0 ? (
        <Card>
          <EmptyState
            title="차단한 크리에이터가 없어요"
            description="크리에이터 프로필이나 피드에서 차단하면 여기에 표시돼요."
            icon={<span className="text-2xl">🔕</span>}
          />
        </Card>
      ) : (
        <div className="overflow-hidden rounded-lg border border-outline">
          {blocks.map((b, i) => (
            <div key={b.creatorId}>
              {i > 0 ? <Divider /> : null}
              <div className="flex items-center gap-3 px-4 py-3">
                <Avatar fallback={b.name.slice(0, 1)} tone={b.handle} />
                <div className="flex min-w-0 flex-1 flex-col">
                  <Link
                    href={`/creator/${b.handle}`}
                    className="truncate text-body-l text-on-surface hover:underline"
                  >
                    {b.name}
                  </Link>
                  <span className="truncate text-caption text-on-surface-variant">@{b.handle}</span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onUnblock(b.creatorId, b.handle, b.name)}
                  disabled={unblock.isPending}
                >
                  차단 해제
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-center text-caption text-on-surface-variant">
        ※ 차단하면 해당 크리에이터의 포스트·활동이 보이지 않고 팔로우가 자동 해제돼요.
      </p>
    </div>
  );
}
