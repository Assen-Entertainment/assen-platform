"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Chip, MonetizableItem, EmptyState, LoadMore } from "@/components/ui";
import { Reveal, Stagger, StaggerItem } from "@/components/motion/motion-primitives";
import { useProducts, useShippingCheckoutAvailable } from "@/lib/api/queries";
import type { Page, Product } from "@/lib/api";

/** 필터 — 상품 type 기준(전체 + 6타입 중 스토어 노출분). */
const FILTERS = [
  { label: "전체", value: "all" },
  { label: "굿즈", value: "goods" },
  { label: "디지털", value: "digital" },
  { label: "체험", value: "experience" },
  { label: "티켓", value: "ticket" },
  { label: "쿠폰", value: "coupon" },
] as const;

export function StoreView({ products }: { products: Page<Product> }) {
  const router = useRouter();
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useProducts(undefined, products);
  // 배송(굿즈) 결제 게이트(ASS-287) — 서버 capability가 열려 있다고 확인되기 전까지 굿즈 구매 CTA를 막는다.
  const shippingAvailable = useShippingCheckoutAvailable();
  const list = data ?? products.items;
  const [f, setF] = React.useState<string>("all");
  const items = f === "all" ? list : list.filter((p) => p.type === f);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <Reveal className="flex flex-col gap-4">
        <h1 className="text-headline text-on-surface">스토어</h1>
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((x) => (
            <Chip key={x.value} selected={f === x.value} onClick={() => setF(x.value)}>
              {x.label}
            </Chip>
          ))}
        </div>
      </Reveal>
      {items.length ? (
        // 스태거드 진입(R13 모션 확장) — 그리드 카드가 순차로 떠오른다. 카드 자체 hover 리프트와
        // 중복을 피하려 StaggerItem lift는 생략(MonetizableItem이 -translate-y 담당). reduced-motion=MotionProvider.
        <Stagger className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4" amount={0.06}>
          {items.map((it) => {
            // 굿즈는 배송 결제가 열려 있을 때만 구매 CTA 활성 — 준비 중이면 비활성 + "준비 중" 라벨.
            const goodsGated = it.type === "goods" && !shippingAvailable;
            return (
            <StaggerItem key={it.id}>
              <MonetizableItem
                type={it.type}
                title={it.title}
                price={`₩${it.price.toLocaleString("ko-KR")}`}
                meta={it.soldOut ? "품절" : it.meta}
                actionDisabled={goodsGated}
                ctaLabel={goodsGated ? "준비 중" : undefined}
                // 크리에이터명 표기 + 프로필 링크(핸들 있을 때). 전역 상품(크리에이터 없음)은 생략.
                creator={
                  it.creatorName ? (
                    it.creatorHandle ? (
                      <Link href={`/creator/${it.creatorHandle}`} className="hover:text-on-surface hover:underline">
                        {it.creatorName}
                      </Link>
                    ) : (
                      it.creatorName
                    )
                  ) : undefined
                }
                onAction={() => router.push(`/store/${it.id}`)}
              />
            </StaggerItem>
            );
          })}
        </Stagger>
      ) : (
        <EmptyState title="상품이 없어요" description="다른 카테고리를 선택해 보세요." />
      )}
      {/* 무한 스크롤 sentinel + 폴백 버튼(필터는 클라, 로드는 전체 상품 커서). */}
      <LoadMore
        hasNextPage={hasNextPage}
        isFetchingNextPage={isFetchingNextPage}
        onLoadMore={() => fetchNextPage()}
        itemCount={list.length}
      />
    </div>
  );
}
