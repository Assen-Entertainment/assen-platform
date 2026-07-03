import Link from "next/link";
import { Divider, StatusChip, EmptyState, Button } from "@/components/ui";
import { getOrders } from "@/lib/api";
import { won } from "@/lib/checkout";
import { orderStatusMeta } from "./status";

/** Orders — 주문 내역(lib/api mock). 항목 클릭 → 주문 상세. */
export default async function OrdersPage() {
  const orders = await getOrders();
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <h1 className="text-headline text-on-surface">주문 내역</h1>
      {orders.length ? (
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
