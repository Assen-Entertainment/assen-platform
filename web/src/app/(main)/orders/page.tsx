import { Badge, Divider } from "@/components/ui";

const ORDERS = [
  { id: "ASN-1024", item: "아크릴 스탠드 외 1건", date: "2026-06-28", price: "₩21,000", status: "배송 중", variant: "primary" },
  { id: "ASN-1019", item: "고해상도 화보집", date: "2026-06-20", price: "₩9,900", status: "완료", variant: "success" },
  { id: "ASN-1003", item: "포토카드 팬사인", date: "2026-06-10", price: "₩30,000", status: "취소", variant: "error" },
] as const;

/** Orders — 주문 내역. E4. */
export default function OrdersPage() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <h1 className="text-headline text-on-surface">주문 내역</h1>
      <div className="overflow-hidden rounded-lg border border-outline">
        {ORDERS.map((o, i) => (
          <div key={o.id}>
            {i > 0 ? <Divider /> : null}
            <div className="flex items-center justify-between gap-3 p-4">
              <div className="flex min-w-0 flex-col gap-0.5">
                <span className="line-clamp-1 text-label text-on-surface">{o.item}</span>
                <span className="text-caption text-on-surface-variant">{o.id} · {o.date}</span>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <Badge variant={o.variant}>{o.status}</Badge>
                <span className="text-title-m tabular-nums text-on-surface">{o.price}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
