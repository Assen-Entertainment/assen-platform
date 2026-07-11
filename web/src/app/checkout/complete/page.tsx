import Link from "next/link";
import { notFound } from "next/navigation";
import { Button, Card, CardBody, Divider, SuccessCheck } from "@/components/ui";
import { getOrder, getCapabilities } from "@/lib/api";
import { config } from "@/lib/config";
import { won } from "@/lib/checkout";

/** 결제 완료 — E5 딜라이트 목업(gradient.brand + 성취 체크 애니메이션). ※실제 결제 미연동(게이트). */
export default async function CheckoutComplete({
  searchParams,
}: {
  searchParams: Promise<{ order?: string }>;
}) {
  const { order } = await searchParams;
  const live = Boolean(config.apiUrl);
  // 실 주문이면 서버 스냅샷(금액·배송지) 조회 — mock 주문번호/비로그인은 undefined(요약 생략).
  const detail = order ? await getOrder(order) : undefined;
  // 라이브에서는 서버 확인된 주문만 완료 화면을 낸다 — 위조/미지의 ?order= 는 성공을 날조하지 않고 404(ASS-287).
  if (live && !detail) notFound();
  // 배송(굿즈) 결제 게이트(ASS-287) — 준비 중이면 "무료배송" 문구를 노출하지 않는다.
  const { shippingCheckoutAvailable } = await getCapabilities();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-surface p-8 text-center">
      <SuccessCheck label="주문 완료" />
      <h1 className="text-headline text-on-surface">주문이 완료됐어요!</h1>
      {order ? (
        <p className="text-body-m text-on-surface-variant">
          주문번호 <span className="font-medium tabular-nums text-on-surface">{order}</span>
        </p>
      ) : null}

      {/* 주문 요약 — 서버 계약(subtotal + 배송비 = total). 배송 상품이면 배송지 스냅샷도 노출. */}
      {detail ? (
        <Card className="w-full max-w-sm text-left">
          <CardBody className="flex flex-col gap-2">
            <div className="flex items-center justify-between text-body-m">
              <span className="text-on-surface-variant">상품 금액</span>
              <span className="tabular-nums text-on-surface">{won(detail.subtotal)}</span>
            </div>
            {detail.shipping > 0 || (shippingCheckoutAvailable && detail.shippingAddress) ? (
              <div className="flex items-center justify-between text-body-m">
                <span className="text-on-surface-variant">배송비</span>
                <span className="tabular-nums text-on-surface">
                  {detail.shipping > 0 ? won(detail.shipping) : "무료"}
                </span>
              </div>
            ) : null}
            <Divider className="my-1" />
            <div className="flex items-center justify-between">
              <span className="text-title-m text-on-surface">총 결제금액</span>
              <span className="text-title-m tabular-nums text-primary">{won(detail.total)}</span>
            </div>
            {detail.shippingAddress ? (
              <>
                <Divider className="my-1" />
                <span className="text-label text-on-surface">배송지</span>
                <p className="text-body-s text-on-surface-variant">
                  {detail.shippingAddress.recipientName} · {detail.shippingAddress.recipientPhone}
                </p>
                <p className="text-body-s text-on-surface-variant">
                  ({detail.shippingAddress.postalCode}) {detail.shippingAddress.address1}
                  {detail.shippingAddress.address2 ? ` ${detail.shippingAddress.address2}` : ""}
                </p>
              </>
            ) : null}
          </CardBody>
        </Card>
      ) : null}

      <p className="text-body-m text-on-surface-variant">주문 내역은 마이페이지에서 확인할 수 있어요.</p>
      <div className="mt-2 flex gap-2">
        <Button variant="outline" asChild>
          <Link href="/orders">주문 내역</Link>
        </Button>
        <Button asChild>
          <Link href="/discovery">계속 둘러보기</Link>
        </Button>
      </div>
      <p className="mt-2 text-caption text-on-surface-variant">※ 데모 — 실제 결제 미연동(게이트)</p>
    </main>
  );
}
