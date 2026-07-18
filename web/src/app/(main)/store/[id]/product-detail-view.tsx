"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Badge,
  Button,
  PriceLabel,
  QuantityStepper,
  OptionSwatch,
  LockedOverlay,
  MediaImage,
  RefundPolicyNotice,
  BottomCTA,
  Divider,
  type MonetizableItemType,
} from "@/components/ui";
import { useProduct, useShippingCheckoutAvailable } from "@/lib/api/queries";
import { useSession } from "@/lib/session";
import { won } from "@/lib/checkout";
import { PRODUCT_TYPE_LABEL } from "@/lib/product-labels";
import type { Product } from "@/lib/api";

/** 타입별 상세 메타(CTA 라벨·안내 문구). 태그 라벨은 PRODUCT_TYPE_LABEL 공용. 6타입 분기. */
const TYPE_META: Record<MonetizableItemType, { cta: string; note: string }> = {
  goods: { cta: "구매하기", note: "배송 상품 · 결제 후 발송" },
  digital: { cta: "구매하기", note: "결제 즉시 다운로드" },
  experience: { cta: "예약하기", note: "일정 확인 후 진행" },
  ticket: { cta: "구매하기", note: "예매 후 관람 링크 발송" },
  coupon: { cta: "받기", note: "발급형 · 유효기간 확인" },
  membership: { cta: "구독하기", note: "정기 결제" },
};

/** 수량 선택 허용 타입(물리/좌석 성격). 나머지는 1개 고정. */
const QTY_TYPES: MonetizableItemType[] = ["goods", "ticket", "experience"];

export function ProductDetailView({ product }: { product: Product }) {
  const router = useRouter();
  const { user, mounted } = useSession();
  const adultVerified = user?.adultVerified === true;
  const { data } = useProduct(product.id, product);
  const shippingAvailable = useShippingCheckoutAvailable();
  const p = data ?? product;
  const meta = TYPE_META[p.type];
  const label = PRODUCT_TYPE_LABEL[p.type];
  const soldOut = Boolean(p.soldOut) || p.stock === 0;
  // 무료 획득(ASS-297) — pricing_kind=free면 CTA 라벨을 "무료로 받기/시작하기"로. 체크아웃이 무료 획득을 처리한다.
  const isFree = p.pricingKind === "free";
  const ctaLabel = isFree ? (p.type === "membership" ? "무료로 시작하기" : "무료로 받기") : meta.cta;
  // 배송(굿즈) 결제 게이트(ASS-287) — 서버 capability가 열렸다고 확인되기 전까지 굿즈 구매를 막는다(배송 PII 폼 도달 차단).
  const shippingBlocked = p.type === "goods" && !shippingAvailable;
  // 19+ 방어 게이트 — 서버가 이미 미인증 뷰어에게 숨기지만 UI도 구매·미디어를 잠근다.
  // 세션 복원 전(mounted=false)엔 판정 보류 — 인증 뷰어에게 블러→언블러 플래시 방지(실누출 0, 시각 개선).
  const adultBlocked = mounted && Boolean(p.isAdult) && !adultVerified;
  const allowQty = QTY_TYPES.includes(p.type) && !soldOut;
  const [qty, setQty] = React.useState(1);
  const [option, setOption] = React.useState<string | null>(p.options?.[0] ?? null);

  const total = p.price * (allowQty ? qty : 1);

  const buy = () => {
    if (soldOut || p.locked || adultBlocked || shippingBlocked) return;
    const optParam = option ? `&opt=${encodeURIComponent(option)}` : "";
    router.push(`/checkout?item=${encodeURIComponent(p.id)}&qty=${qty}${optParam}`);
  };

  /** 성인 미인증=인증 유도 / 잠금=구독 유도 / 품절=비활성(배송 게이트보다 우선) / 배송 준비 중=비활성 / 그 외=구매 CTA.
   *  ※품절은 미디어 배지와 일치하도록 shippingBlocked보다 먼저 판정한다(품절 굿즈가 "배송 준비 중"으로 뜨던 모순 제거). */
  const primaryCta = adultBlocked ? (
    <Button size="lg" className="w-full" asChild>
      <Link href="/age-gate">성인 인증하고 보기</Link>
    </Button>
  ) : p.locked ? (
    <Button size="lg" className="w-full" asChild>
      <Link href="/membership">멤버십 구독하고 보기</Link>
    </Button>
  ) : soldOut ? (
    <Button size="lg" className="w-full" disabled>
      품절
    </Button>
  ) : shippingBlocked ? (
    <Button size="lg" className="w-full" disabled>
      배송 결제 준비 중이에요
    </Button>
  ) : (
    <Button size="lg" className="w-full" onClick={buy}>
      {ctaLabel}
    </Button>
  );

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 pb-40 lg:pb-6">
      <nav className="text-body-s text-on-surface-variant" aria-label="위치">
        <Link href="/store" className="hover:text-on-surface">
          스토어
        </Link>
        <span className="px-1" aria-hidden>
          /
        </span>
        <span className="text-on-surface">{label}</span>
      </nav>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* 미디어 — 실 이미지 우선, 없으면 프리미엄 톤 커버(저채도 + 그레인 + 상품명 모노그램, 스토어 카드와 동일). */}
        <MediaImage
          src={p.mediaUrl}
          alt={p.title}
          seed={p.title}
          className="aspect-square w-full rounded-lg"
        >
          {soldOut ? (
            <span className="absolute left-3 top-3 rounded-full bg-black/60 px-2.5 py-1 text-caption font-medium text-white">
              품절
            </span>
          ) : null}
          {adultBlocked ? (
            <LockedOverlay
              title="성인(19+) 콘텐츠"
              description="본인인증 후 볼 수 있어요."
              cta={
                <Button size="sm" asChild>
                  <Link href="/age-gate">성인 인증하기</Link>
                </Button>
              }
            />
          ) : p.locked ? (
            <LockedOverlay
              description="이 콘텐츠는 멤버십 구독자에게만 공개됩니다."
              cta={
                <Button size="sm" asChild>
                  <Link href="/membership">멤버십 보기</Link>
                </Button>
              }
            />
          ) : null}
        </MediaImage>

        {/* 정보 */}
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Badge variant="primary" className="self-start">
              {label}
            </Badge>
            <h1 className="text-headline text-on-surface">{p.title}</h1>
            {p.creatorName ? (
              p.creatorHandle ? (
                <Link
                  href={`/creator/${p.creatorHandle}`}
                  className="text-body-s text-on-surface-variant hover:text-on-surface hover:underline"
                >
                  {p.creatorName}
                </Link>
              ) : (
                <p className="text-body-s text-on-surface-variant">{p.creatorName}</p>
              )
            ) : null}
          </div>

          <div className="flex items-baseline gap-2">
            <PriceLabel amount={p.price} suffix={p.type === "membership" ? "/월" : undefined} className="text-title-l" />
            {p.meta ? <span className="text-body-s text-on-surface-variant">{p.meta}</span> : null}
          </div>
          <p className="text-caption text-on-surface-variant">{meta.note}</p>

          <Divider />

          {p.options && p.options.length ? (
            <div className="flex flex-col gap-2">
              <span className="text-label text-on-surface">옵션</span>
              <div className="flex flex-wrap gap-2">
                {p.options.map((o) => (
                  <OptionSwatch key={o} selected={option === o} disabled={soldOut} onClick={() => setOption(o)}>
                    {o}
                  </OptionSwatch>
                ))}
              </div>
            </div>
          ) : null}

          {allowQty ? (
            <div className="flex items-center justify-between">
              <span className="text-label text-on-surface">수량</span>
              <QuantityStepper value={qty} onChange={setQty} max={p.stock ?? 99} />
            </div>
          ) : null}

          <div className="flex items-center justify-between rounded-lg bg-surface-container p-3">
            <span className="text-body-m text-on-surface-variant">합계</span>
            <span className="text-title-l tabular-nums text-primary">{won(total)}</span>
          </div>

          {/* lg+ 인라인 CTA(모바일은 하단 BottomCTA) */}
          <div className="hidden lg:block">{primaryCta}</div>
        </div>
      </div>

      {p.description ? (
        <section className="flex flex-col gap-2">
          <h2 className="text-title-l text-on-surface">상품 정보</h2>
          <p className="whitespace-pre-wrap text-body-m text-on-surface">{p.description}</p>
        </section>
      ) : null}

      <RefundPolicyNotice />

      {/* 모바일(<lg) 하단 고정 CTA */}
      <BottomCTA>
        <div className="flex flex-col">
          <span className="text-caption text-on-surface-variant">합계</span>
          <span className="text-title-m tabular-nums text-on-surface">{won(total)}</span>
        </div>
        <div className="flex-1">{primaryCta}</div>
      </BottomCTA>
    </div>
  );
}
