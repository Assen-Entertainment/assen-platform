"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import { Chip, MonetizableItem, EmptyState, Button } from "@/components/ui";
import { useProducts } from "@/lib/api/queries";
import type { Product } from "@/lib/api";

/** 필터 — 상품 type 기준(전체 + 6타입 중 스토어 노출분). */
const FILTERS = [
  { label: "전체", value: "all" },
  { label: "굿즈", value: "goods" },
  { label: "디지털", value: "digital" },
  { label: "체험", value: "experience" },
  { label: "티켓", value: "ticket" },
  { label: "쿠폰", value: "coupon" },
] as const;

export function StoreView({ products }: { products: Product[] }) {
  const router = useRouter();
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useProducts(undefined, products);
  const list = data ?? products;
  const [f, setF] = React.useState<string>("all");
  const items = f === "all" ? list : list.filter((p) => p.type === f);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <h1 className="text-headline text-on-surface">스토어</h1>
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((x) => (
          <Chip key={x.value} selected={f === x.value} onClick={() => setF(x.value)}>
            {x.label}
          </Chip>
        ))}
      </div>
      {items.length ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {items.map((it) => (
            <MonetizableItem
              key={it.id}
              type={it.type}
              title={it.title}
              price={`₩${it.price.toLocaleString("ko-KR")}`}
              meta={it.soldOut ? "품절" : it.meta}
              onAction={() => router.push(`/store/${it.id}`)}
            />
          ))}
        </div>
      ) : (
        <EmptyState title="상품이 없어요" description="다른 카테고리를 선택해 보세요." />
      )}
      {/* 더보기 — 커서 다음 페이지가 있을 때만(필터는 클라이언트, 로드는 전체 상품 커서). */}
      {hasNextPage ? (
        <div className="flex justify-center">
          <Button variant="outline" onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
            {isFetchingNextPage ? "불러오는 중…" : "더보기"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
