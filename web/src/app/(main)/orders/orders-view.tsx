"use client";
import Link from "next/link";
import { Divider, StatusChip, EmptyState, Button } from "@/components/ui";
import { useOrders } from "@/lib/api/queries";
import { won } from "@/lib/checkout";
import { orderStatusMeta } from "./status";
import type { Order } from "@/lib/api";

/**
 * Orders — 주문 내역(커서 무한 로드). SSR `initialOrders` 하이드레이션 + 더보기 버튼.
 * mock 모드는 단일 페이지(더보기 없음)로 기존 서버 렌더와 동일 표시(회귀 0).
 */
export function OrdersView({ initialOrders }: { initialOrders: Order[] }) {
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useOrders(initialOrders);
  const orders = data ?? initialOrders;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <h1 className="text-headline text-on-surface">주문 내역</h1>
      {orders.length ? (
        <>
          <div className="overflow-hidden rounded-lg border border-outline">
            {orders.map((o, i) => {
              const s = orderStatusMeta(o.status);
              const summary =
                o.items[0].title + (o.items.length > 1 ? ` 외 ${o.items.length - 1}건` : "");
              return (
                <div key={o.id}>
                  {i > 0 ? <Divider /> : null}
                  <Link href={`/orders/${o.id}`} className="block transition-colors hover:bg-surface-container-high">
                    <div className="flex items-center justify-between gap-3 p-4">
                      <div className="flex min-w-0 flex-col gap-0.5">
                        <span className="line-clamp-1 text-label text-on-surface">{summary}</span>
                        <span className="text-caption text-on-surface-variant">
                          {o.id} · {o.createdAt}
                        </span>
                      </div>
                      <div className="flex shrink-0 items-center gap-3">
                        <StatusChip variant={s.variant}>{s.label}</StatusChip>
                        <span className="text-title-m tabular-nums text-on-surface">{won(o.total)}</span>
                      </div>
                    </div>
                  </Link>
                </div>
              );
            })}
          </div>
          {/* 더보기 — 커서 다음 페이지가 있을 때만(무한 쿼리 fetchNextPage). */}
          {hasNextPage ? (
            <div className="flex justify-center">
              <Button variant="outline" onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
                {isFetchingNextPage ? "불러오는 중…" : "더보기"}
              </Button>
            </div>
          ) : null}
        </>
      ) : (
        <EmptyState
          title="주문 내역이 없어요"
          description="마음에 드는 아이템을 둘러보세요."
          action={
            <Button asChild>
              <Link href="/store">스토어 가기</Link>
            </Button>
          }
        />
      )}
    </div>
  );
}
