"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Chip, MonetizableItem, EmptyState, LoadMore, Spinner } from "@/components/ui";
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
  const filtering = f !== "all";
  const items = filtering ? list.filter((p) => p.type === f) : list;
  // 카테고리 필터는 클라에 로드된 목록에만 적용된다 — 카탈로그가 여러 페이지면 뒤 페이지의 매칭이
  // 누락되고, 로드된 1페이지에 해당 타입이 없으면 "상품 없어요" 빈 상태와 "더보기" 버튼이 동시에 뜬다.
  // 필터 활성 시 남은 페이지를 모두 당겨 필터가 전체 집합을 보게 한다(모순 제거·후페이지 도달 보장, #9).
  React.useEffect(() => {
    if (filtering && hasNextPage && !isFetchingNextPage) void fetchNextPage();
  }, [filtering, hasNextPage, isFetchingNextPage, fetchNextPage]);
  // 필터 집합이 아직 완성 전(더 당길 페이지 남음)이면 성급한 빈 상태 대신 로딩을 보여준다.
  const filteredIncomplete = filtering && hasNextPage;

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
            // 품절이면 최우선으로 비활성 + "품절"(배송 게이트보다 우선) — 품절 상품에 활성 구매
            // 버튼이 뜨던 blindspot 방지. 굿즈는 배송 결제가 열려 있을 때만 CTA 활성(준비 중 라벨).
            const soldOut = Boolean(it.soldOut) || it.stock === 0;
            const goodsGated = it.type === "goods" && !shippingAvailable;
            return (
            <StaggerItem key={it.id}>
              <MonetizableItem
                type={it.type}
                title={it.title}
                price={`₩${it.price.toLocaleString("ko-KR")}`}
                meta={soldOut ? "품절" : it.meta}
                actionDisabled={soldOut || goodsGated}
                ctaLabel={soldOut ? "품절" : goodsGated ? "준비 중" : undefined}
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
      ) : filteredIncomplete ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : (
        <EmptyState title="상품이 없어요" description="다른 카테고리를 선택해 보세요." />
      )}
      {/* 무한 스크롤은 '전체'에서만 — 필터 중엔 위 effect가 남은 페이지를 자동 로드하므로 수동 더보기를 숨긴다. */}
      {!filtering ? (
        <LoadMore
          hasNextPage={hasNextPage}
          isFetchingNextPage={isFetchingNextPage}
          onLoadMore={() => fetchNextPage()}
          itemCount={list.length}
        />
      ) : null}
    </div>
  );
}
