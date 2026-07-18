// ※ 실결제/PG 연동은 대표·법무 게이트, 본 플로우는 UI mock입니다.
import Link from "next/link";
import { getProduct, getMembershipTiers, getCreator } from "@/lib/api";
import { summarizeProduct, summarizeTier, type OrderSummary } from "@/lib/checkout";
import { Button } from "@/components/ui";
import { CheckoutView } from "./checkout-view";

/**
 * Checkout — `?item={id}&qty=&opt=` 또는 `?tier={id}&creator=` 쿼리로 주문 요약을 구성.
 * 서버에서 대상 fetch + 요약 계산 → 클라 뷰(결제수단·정책·mock 처리).
 */
export default async function CheckoutPage({
  searchParams,
}: {
  searchParams: Promise<{ item?: string; qty?: string; opt?: string; tier?: string; creator?: string }>;
}) {
  const sp = await searchParams;
  const hasTarget = Boolean(sp.item || sp.tier);
  const qtyParam = Math.max(1, parseInt(sp.qty ?? "1", 10) || 1);
  let summary: OrderSummary | null = null;

  if (sp.item) {
    const product = await getProduct(sp.item);
    if (product) {
      summary = summarizeProduct(product, qtyParam, sp.opt);
    }
  } else if (sp.tier) {
    const tiers = await getMembershipTiers();
    const tier = tiers.find((t) => t.id === sp.tier);
    if (tier) {
      // 구독 대상 크리에이터를 명시(아바타·이름·티어를 결제 확인 화면에 노출 — 대상 불투명 해소).
      const creator = sp.creator ? await getCreator(sp.creator) : undefined;
      summary = summarizeTier(tier, creator ?? undefined);
    }
  }

  // 대상 파라미터는 있으나 해결 실패(없는 상품/티어) → 데모 폴백 대신 명시적 안내.
  if (!summary && hasTarget) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-surface-container-high px-4 text-center">
        <h1 className="text-headline text-on-surface">상품을 찾을 수 없어요</h1>
        <p className="max-w-sm text-body-m text-on-surface-variant">
          요청하신 상품이 존재하지 않거나 판매가 종료되었어요. 스토어에서 다른 상품을 둘러보세요.
        </p>
        <Button asChild>
          <Link href="/store">스토어로 이동</Link>
        </Button>
      </main>
    );
  }

  // 파라미터가 전혀 없을 때만 데모 폴백(스탠드얼론 /checkout 방문 대비).
  if (!summary) {
    const fallback = await getProduct("p1");
    summary = fallback ? summarizeProduct(fallback, 1) : summarizeProduct(
      { id: "demo", type: "goods", title: "데모 상품", price: 18000 },
      1,
    );
  }

  // 결제 대상 식별자 — 실 주문/구독 호출용(파라미터 해결 성공 시에만). 없으면 mock 결제.
  const target =
    summary && sp.item
      ? ({ kind: "product", productId: sp.item, qty: qtyParam, option: sp.opt } as const)
      : summary && sp.tier
        ? ({ kind: "membership", tierId: sp.tier } as const)
        : undefined;

  return <CheckoutView summary={summary} target={target} />;
}
