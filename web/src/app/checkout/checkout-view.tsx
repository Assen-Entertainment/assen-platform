"use client";
// ※ 실결제/PG 연동은 대표·법무 게이트, 본 플로우는 UI mock입니다.
//   표시 금액은 서버 계약(subtotal + shipping = total)을 그대로 미러합니다 — 클라에서 배송비/VAT를
//   날조하지 않습니다. KR 관행상 표시가는 VAT 포함가이므로 별도 VAT 행을 두지 않습니다.
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
  Avatar,
  TextField,
  PaymentIcon,
  RefundPolicyNotice,
  AutoPayConsentSheet,
  IdentityVerifyBanner,
  TermsLinkFooter,
  type PaymentMethod,
} from "@/components/ui";
import Link from "next/link";
import { useToast } from "@/components/ui/use-toast";
import { config } from "@/lib/config";
import { ApiError, apiErrorMessage, ERROR_CODES, type ShippingAddress } from "@/lib/api";
import {
  useCreateOrder,
  useCreateOrderFree,
  useSubscribe,
  useSubscribeFree,
  useShippingCheckoutAvailable,
} from "@/lib/api/queries";
import { useSession } from "@/lib/session";
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

/** 빈 배송지 초기값. */
const EMPTY_SHIPPING: ShippingAddress = {
  recipientName: "",
  recipientPhone: "",
  postalCode: "",
  address1: "",
  address2: "",
};

export function CheckoutView({ summary, target }: { summary: OrderSummary; target?: CheckoutTarget }) {
  const router = useRouter();
  const { toast } = useToast();
  const { user } = useSession();
  const adultVerified = user?.adultVerified === true;
  const createOrder = useCreateOrder();
  const createOrderFree = useCreateOrderFree();
  const subscribe = useSubscribe();
  const subscribeFree = useSubscribeFree();
  const live = Boolean(config.apiUrl);
  const isMembership = summary.kind === "membership";
  // 무료 획득(ASS-297) — 결제수단·정기결제 동의 UI를 숨기고 무료 hook을 호출한다. 배송(굿즈)은 유지.
  const isFree = summary.free === true;
  const isGoods = summary.kind === "product" && summary.productType === "goods";
  // 배송 상품(굿즈)만 배송지 입력 필요 — 디지털/티켓/쿠폰/체험/멤버십은 미노출.
  const needsShipping = isGoods;
  // 배송(굿즈) 결제 게이트(ASS-287) — 서버 capability가 열렸다고 확인되기 전까지 배송지 PII 폼에 도달시키지 않는다.
  const shippingAvailable = useShippingCheckoutAvailable();
  // 굿즈 결제 시도 중 서버가 503(ShippingCheckoutUnavailable)을 반환한 레이스 — 준비 중 상태로 전환.
  const [raceBlocked, setRaceBlocked] = React.useState(false);
  const [pay, setPay] = React.useState<PaymentMethod>("card");
  const [agree, setAgree] = React.useState(false);
  const [autoPay, setAutoPay] = React.useState(false);
  const [processing, setProcessing] = React.useState(false);
  const [ship, setShip] = React.useState<ShippingAddress>(EMPTY_SHIPPING);
  // 배송지 미완성 상태에서 결제 시도 시에만 인라인 오류 노출(첫 렌더부터 빨갛게 뜨지 않도록).
  const [shipTouched, setShipTouched] = React.useState(false);
  const timer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  React.useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const setShipField = (key: keyof ShippingAddress) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setShip((s) => ({ ...s, [key]: e.target.value }));

  // 필수: 받는분·연락처·우편번호·기본주소(상세주소는 선택). 서버 422 방어 전 클라 1차 검증.
  const shippingComplete =
    ship.recipientName.trim() !== "" &&
    ship.recipientPhone.trim() !== "" &&
    ship.postalCode.trim() !== "" &&
    ship.address1.trim() !== "";

  // 무료 멤버십은 정기결제 동의(autoPay)를 요구하지 않는다(결제 자체가 없음).
  const canPay = agree && (isFree || !isMembership || autoPay) && !processing;

  // 422(주문 불가/품절/재고/멤버십 전용/배송지 누락/중복 구독)는 서버 error code로 안내(문자열 매칭 제거,
  // ProductNotOrderable·OutOfStock·InsufficientStock·MembershipOnlyProduct·ShippingAddressRequired·
  // DuplicateSubscription 등). 코드가 없으면 서버 detail(표시용) → 일반 폴백. 401은 전역 세션 가드가 처리.
  const onCheckoutError = (e: unknown) => {
    setProcessing(false);
    if (e instanceof ApiError) {
      // 배송 결제 준비 중(503 ShippingCheckoutUnavailable) — 일반 오류 토스트 대신 준비 중 상태로 전환(레이스 방어).
      if (e.code === ERROR_CODES.ShippingCheckoutUnavailable) {
        setRaceBlocked(true);
        return;
      }
      if (e.status === 422) {
        const fallback = isMembership
          ? "이 멤버십은 이미 구독하고 있어요."
          : "품절이거나 재고가 부족하거나 판매가 마감됐어요.";
        toast({
          title: isMembership ? "구독할 수 없어요" : "주문할 수 없어요",
          description: apiErrorMessage(e, undefined, fallback),
        });
        return;
      }
      if (e.status === 401) return;
    }
    toast({ title: "결제를 완료하지 못했어요", description: "잠시 후 다시 시도해 주세요." });
  };

  const submit = () => {
    if (!canPay) return;
    // 배송 상품인데 배송지가 미완성이면 결제 진행 전 차단(서버 422 전 클라 안내).
    if (needsShipping && !shippingComplete) {
      setShipTouched(true);
      toast({ title: "배송지를 입력해 주세요", description: "받는 분·연락처·우편번호·주소를 확인해 주세요." });
      return;
    }
    setProcessing(true);

    // 라이브 백엔드 + 대상 식별자가 있으면 실 주문/구독. 무료면 결제 없는 무료 획득 경로(ASS-297),
    // 아니면 유료(mock 결제 확정 — 실 PG·금액이동 없음).
    if (live && target?.kind === "product") {
      const orderMut = isFree ? createOrderFree : createOrder;
      orderMut.mutate(
        {
          productId: target.productId,
          qty: target.qty,
          option: target.option,
          shipping: needsShipping ? ship : undefined,
        },
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
      const subMut = isFree ? subscribeFree : subscribe;
      subMut.mutate(
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

  const initial = summary.creatorName?.slice(0, 1) ?? "";

  // 배송(굿즈) 결제가 준비 중이면 배송지 PII 폼·결제 UI 대신 준비 중 상태만 노출한다.
  // 직접 `/checkout?...` 접근·파라미터 없는 데모 굿즈 폴백도 모두 이 경로로 수렴(PII 폼에 절대 도달 안 함).
  if (isGoods && (!shippingAvailable || raceBlocked)) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-surface-container-high px-4 text-center">
        <h1 className="text-headline text-on-surface">배송 결제 준비 중이에요</h1>
        <p className="max-w-sm text-body-m text-on-surface-variant">
          배송 상품 결제 흐름을 준비하고 있어요. 지금은 배송이 필요 없는 디지털·멤버십 상품을 이용해 주세요.
        </p>
        <Button asChild>
          <Link href="/store">스토어로 돌아가기</Link>
        </Button>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-surface-container-high py-10">
      <div className="mx-auto flex max-w-lg flex-col gap-4 px-4">
        <h1 className="text-headline text-on-surface">주문 / 결제</h1>

        {/* 구독 대상 크리에이터 명시 — 아바타+이름+티어(대상 불투명 해소). */}
        {isMembership && summary.creatorName ? (
          <Card>
            <CardBody className="flex items-center gap-3">
              <Avatar fallback={initial} tone={summary.creatorHandle ?? summary.creatorName} size="lg" />
              <div className="flex min-w-0 flex-col">
                <span className="text-caption text-on-surface-variant">구독 크리에이터</span>
                <span className="line-clamp-1 text-body-l text-on-surface">{summary.creatorName}</span>
                {summary.tierName ? (
                  <span className="text-body-s text-on-surface-variant">{summary.tierName} 멤버십</span>
                ) : null}
              </div>
            </CardBody>
          </Card>
        ) : null}

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
                    : `${won(summary.unitPrice)} × ${summary.qty}개${summary.option ? ` · ${summary.option}` : ""}`}
                </span>
              </div>
              {/* 행 합계 = 단가 × 수량(멤버십은 월 정기 금액). */}
              <span className="shrink-0 text-title-m tabular-nums text-on-surface">
                {won(isMembership ? summary.unitPrice : summary.subtotal)}
              </span>
            </div>
          </CardBody>
        </Card>

        {/* 배송지 — 배송 상품(굿즈)만 노출. 서버 계약: 누락 시 422 ShippingAddressRequired. */}
        {needsShipping ? (
          <Card>
            <CardBody className="flex flex-col gap-3">
              <span className="text-title-m text-on-surface">배송지</span>
              <TextField
                label="받는 분"
                value={ship.recipientName}
                onChange={setShipField("recipientName")}
                placeholder="이름"
                maxLength={60}
                error={shipTouched && ship.recipientName.trim() === ""}
                errorText="받는 분을 입력해 주세요."
              />
              <TextField
                label="연락처"
                type="tel"
                value={ship.recipientPhone}
                onChange={setShipField("recipientPhone")}
                placeholder="010-0000-0000"
                maxLength={32}
                error={shipTouched && ship.recipientPhone.trim() === ""}
                errorText="연락처를 입력해 주세요."
              />
              <TextField
                label="우편번호"
                inputMode="numeric"
                value={ship.postalCode}
                onChange={setShipField("postalCode")}
                placeholder="00000"
                maxLength={16}
                error={shipTouched && ship.postalCode.trim() === ""}
                errorText="우편번호를 입력해 주세요."
              />
              <TextField
                label="주소"
                value={ship.address1}
                onChange={setShipField("address1")}
                placeholder="도로명/지번 주소"
                maxLength={200}
                error={shipTouched && ship.address1.trim() === ""}
                errorText="주소를 입력해 주세요."
              />
              <TextField
                label="상세 주소"
                value={ship.address2}
                onChange={setShipField("address2")}
                placeholder="동·호수 등(선택)"
                maxLength={200}
              />
            </CardBody>
          </Card>
        ) : null}

        {/* 결제 수단 — 무료 획득(ASS-297)은 결제가 없어 선택기를 노출하지 않는다. */}
        {isFree ? null : (
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
        )}

        {/* 금액 요약 — 서버 계약 미러(subtotal + 배송비 = total). 무료 획득은 결제 금액이 0(무료 표기). */}
        <Card>
          <CardBody className="flex flex-col gap-2">
            <Row label={isMembership ? "구독 금액" : "상품 금액"} value={isFree ? "무료" : won(summary.subtotal)} />
            {needsShipping ? <Row label="배송비" value={summary.shipping > 0 ? won(summary.shipping) : "무료"} /> : null}
            <Divider className="my-1" />
            <div className="flex items-center justify-between">
              <span className="text-title-m text-on-surface">{isFree ? "결제 금액" : "총 결제금액"}</span>
              <span className="text-title-l tabular-nums text-primary">{isFree ? "무료" : won(summary.total)}</span>
            </div>
            {isFree ? null : <p className="text-caption text-on-surface-variant">부가세(VAT 10%) 포함 금액입니다.</p>}
          </CardBody>
        </Card>

        {/* 정책 컴포넌트 — 무료 멤버십은 정기결제가 없어 자동결제 동의를 노출하지 않는다. */}
        {isMembership && !isFree ? (
          <AutoPayConsentSheet
            checked={autoPay}
            onCheckedChange={setAutoPay}
            summary={`${won(summary.total)} · 매월 자동결제`}
          />
        ) : null}
        <IdentityVerifyBanner
          verified={adultVerified}
          action={
            <Button size="sm" variant="outline" asChild>
              <Link href="/age-gate">본인인증</Link>
            </Button>
          }
        />
        <RefundPolicyNotice />

        <div className="flex items-center gap-2 px-1 text-body-s text-on-surface-variant">
          <Checkbox id="checkout-agree" checked={agree} onCheckedChange={(v) => setAgree(v === true)} />
          <label htmlFor="checkout-agree">
            {isFree ? "주문 내용을 확인했으며 진행에 동의합니다" : "주문 내용을 확인했으며 결제 진행에 동의합니다"}
          </label>
        </div>

        <Button size="lg" disabled={!canPay} className="w-full" onClick={submit}>
          {processing ? (
            <>
              <Spinner className="size-5 text-on-primary" /> {isFree ? "처리 중…" : "결제 처리 중…"}
            </>
          ) : isFree ? (
            isMembership ? "무료로 시작하기" : "무료로 받기"
          ) : (
            `${won(summary.total)} 결제하기`
          )}
        </Button>
        <TermsLinkFooter className="justify-center" />
        {isFree ? null : (
          <p className="text-center text-caption text-on-surface-variant">
            ※ 실결제/PG 연동은 대표·법무 게이트 — 본 결제 흐름은 UI mock입니다.
          </p>
        )}
      </div>
    </main>
  );
}
