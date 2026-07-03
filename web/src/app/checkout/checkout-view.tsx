"use client";
// ※ 실결제/PG 연동은 대표·법무 게이트, 본 플로우는 UI mock입니다.
//   금액·VAT·약관 문구는 placeholder이며 단독 확정 대상이 아닙니다.
import * as React from "react";
import { useRouter } from "next/navigation";
import {
  Card,
  CardBody,
  RadioGroup,
  RadioGroupItem,
  Checkbox,
  Button,
  Divider,
  Spinner,
  PaymentIcon,
  RefundPolicyNotice,
  AutoPayConsentSheet,
  IdentityVerifyBanner,
  TermsLinkFooter,
  type PaymentMethod,
} from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { config } from "@/lib/config";
import { ApiError } from "@/lib/api";
import { useCreateOrder, useSubscribe } from "@/lib/api/queries";
import { mockOrderId, won, type OrderSummary } from "@/lib/checkout";

/** 결제 대상 식별자 — 실 주문/구독 호출용. 없으면 mock 결제로 폴백. */
export type CheckoutTarget =
  | { kind: "product"; productId: string; qty: number; option?: string }
  | { kind: "membership"; tierId: string };

function Row({ label, value, muted }: { label: string; value: string; muted?: boolean }) {
  return (
    <div className="flex items-center justify-between text-body-m">
      <span className="text-on-surface-variant">{label}</span>
      <span className={muted ? "tabular-nums text-on-surface-variant" : "tabular-nums text-on-surface"}>{value}</span>
    </div>
  );
}

const METHODS: PaymentMethod[] = ["card", "bank", "pay"];

export function CheckoutView({ summary, target }: { summary: OrderSummary; target?: CheckoutTarget }) {
  const router = useRouter();
  const { toast } = useToast();
  const createOrder = useCreateOrder();
  const subscribe = useSubscribe();
  const live = Boolean(config.apiUrl);
  const isMembership = summary.kind === "membership";
  const [pay, setPay] = React.useState<PaymentMethod>("card");
  const [agree, setAgree] = React.useState(false);
  const [autoPay, setAutoPay] = React.useState(false);
  const [processing, setProcessing] = React.useState(false);
  const timer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  React.useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const canPay = agree && (!isMembership || autoPay) && !processing;

  // 422(품절/재고/중복)·기타 실패 안내. 401은 전역 세션 가드가 처리.
  const onCheckoutError = (e: unknown) => {
    setProcessing(false);
    if (e instanceof ApiError) {
      if (e.status === 422) {
        // 서버 detail(멤버십 전용/품절/재고 부족 등)을 그대로 노출 — 없으면 일반 안내.
        const fallback = isMembership
          ? "이 멤버십은 이미 구독하고 있어요."
          : "품절이거나 재고가 부족하거나 판매가 마감됐어요.";
        toast({
          title: isMembership ? "구독할 수 없어요" : "주문할 수 없어요",
          description: e.detail ?? fallback,
        });
        return;
      }
      if (e.status === 401) return;
    }
    toast({ title: "결제를 완료하지 못했어요", description: "잠시 후 다시 시도해 주세요." });
  };

  const submit = () => {
    if (!canPay) return;
    setProcessing(true);

    // 라이브 백엔드 + 대상 식별자가 있으면 실 주문/구독(mock 결제 확정 — 실 PG·금액이동 없음).
    if (live && target?.kind === "product") {
      createOrder.mutate(
        { productId: target.productId, qty: target.qty, option: target.option },
        {
          onSuccess: (order) => {
            const id = order?.id ?? mockOrderId();
            router.push(`/checkout/complete?order=${encodeURIComponent(id)}`);
          },
          onError: onCheckoutError,
        },
      );
      return;
    }
    if (live && target?.kind === "membership") {
      subscribe.mutate(
        { tierId: target.tierId },
        {
          onSuccess: () => router.push("/mypage/subscriptions"),
          onError: onCheckoutError,
        },
      );
      return;
    }

    // mock 결제 처리(1초 시뮬레이션) → 완료 페이지 이동. 실제 PG 승인 없음.
    timer.current = setTimeout(() => {
      router.push(`/checkout/complete?order=${encodeURIComponent(mockOrderId())}`);
    }, 1000);
  };

  return (
    <main className="min-h-screen bg-surface-container-high py-10">
      <div className="mx-auto flex max-w-lg flex-col gap-4 px-4">
        <h1 className="text-headline text-on-surface">주문 / 결제</h1>

        {/* 주문 요약 */}
        <Card>
          <CardBody className="flex flex-col gap-3">
            <span className="text-title-m text-on-surface">{isMembership ? "구독 상품" : "주문 상품"}</span>
            <div className="flex items-center justify-between gap-3">
              <div className="flex min-w-0 flex-col">
                <span className="line-clamp-1 text-body-l text-on-surface">{summary.label}</span>
                <span className="text-caption text-on-surface-variant">
                  {isMembership
                    ? "정기 결제(월)"
                    : `수량 ${summary.qty}개${summary.option ? ` · ${summary.option}` : ""}`}
                </span>
              </div>
              <span className="shrink-0 text-title-m tabular-nums text-on-surface">{won(summary.unitPrice)}</span>
            </div>
          </CardBody>
        </Card>

        {/* 결제 수단 */}
        <Card>
          <CardBody className="flex flex-col gap-3">
            <span className="text-title-m text-on-surface">결제 수단</span>
            <RadioGroup value={pay} onValueChange={(v) => setPay(v as PaymentMethod)}>
              {METHODS.map((m) => (
                <label key={m} htmlFor={`pay-${m}`} className="flex items-center gap-2.5 text-body-m text-on-surface">
                  <RadioGroupItem value={m} id={`pay-${m}`} />
                  <PaymentIcon method={m} showLabel />
                </label>
              ))}
            </RadioGroup>
          </CardBody>
        </Card>

        {/* 금액 요약(VAT 분리 placeholder) */}
        <Card>
          <CardBody className="flex flex-col gap-2">
            <Row label={isMembership ? "구독 금액" : "상품 금액"} value={won(summary.subtotal)} />
            {summary.shipping > 0 ? <Row label="배송비" value={won(summary.shipping)} /> : null}
            <Row label="공급가액" value={won(summary.supply)} muted />
            <Row label="부가세(VAT 10%)" value={won(summary.vat)} muted />
            <Divider className="my-1" />
            <div className="flex items-center justify-between">
              <span className="text-title-m text-on-surface">총 결제금액</span>
              <span className="text-title-l tabular-nums text-primary">{won(summary.total)}</span>
            </div>
          </CardBody>
        </Card>

        {/* 정책 컴포넌트 */}
        {isMembership ? (
          <AutoPayConsentSheet
            checked={autoPay}
            onCheckedChange={setAutoPay}
            summary={`${won(summary.total)} · 매월 자동결제`}
          />
        ) : null}
        <IdentityVerifyBanner />
        <RefundPolicyNotice />

        <label className="flex items-center gap-2 px-1 text-body-s text-on-surface-variant">
          <Checkbox checked={agree} onCheckedChange={(v) => setAgree(v === true)} />
          주문 내용을 확인했으며 결제 진행에 동의합니다
        </label>

        <Button size="lg" disabled={!canPay} className="w-full" onClick={submit}>
          {processing ? (
            <>
              <Spinner className="size-5 text-on-primary" /> 결제 처리 중…
            </>
          ) : (
            `${won(summary.total)} 결제하기`
          )}
        </Button>
        <TermsLinkFooter className="justify-center" />
        <p className="text-center text-caption text-on-surface-variant">
          ※ 실결제/PG 연동은 대표·법무 게이트 — 본 결제 흐름은 UI mock입니다.
        </p>
      </div>
    </main>
  );
}
