"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  SegmentedControl,
  CreatorThumbCard,
  MonetizableItem,
  ErrorState,
  CategoryIconRow,
  Shelf,
  Button,
  type CategoryItem,
} from "@/components/ui";
import {
  IllustIcon,
  MusicIcon,
  VtuberIcon,
  GoodsIcon,
  GameIcon,
  PhotoIcon,
  CosplayIcon,
  WritingIcon,
} from "@/lib/icons";
import { useCreators, useProducts } from "@/lib/api/queries";
import type { Creator, Product } from "@/lib/api";

const CATS = [
  { label: "전체", value: "all" },
  { label: "일러스트", value: "일러스트" },
  { label: "뮤직", value: "뮤직" },
  { label: "버튜버", value: "버튜버" },
];

/** 카테고리 아이콘 행(#7) — 콜드스타트 탐색 진입점. 클릭 → 검색으로 이동. */
const CATEGORY_ICONS: CategoryItem[] = [
  { label: "일러스트", value: "일러스트", icon: <IllustIcon /> },
  { label: "뮤직", value: "뮤직", icon: <MusicIcon /> },
  { label: "버튜버", value: "버튜버", icon: <VtuberIcon /> },
  { label: "굿즈", value: "굿즈", icon: <GoodsIcon /> },
  { label: "게임", value: "게임", icon: <GameIcon /> },
  { label: "사진", value: "사진", icon: <PhotoIcon /> },
  { label: "코스프레", value: "코스프레", icon: <CosplayIcon /> },
  { label: "글·소설", value: "글", icon: <WritingIcon /> },
];

/** 팔로워 수 → 사회적 증거 라벨(#12). */
function followers(n: number): string {
  return n >= 1000 ? (n / 1000).toFixed(1).replace(/\.0$/, "") + "k" : String(n);
}

function creatorMeta(c: Creator): string {
  return `${c.category ?? ""} · 팔로워 ${followers(c.followers)}`;
}

export function DiscoveryView({ creators, products }: { creators: Creator[]; products: Product[] }) {
  const router = useRouter();
  const [cat, setCat] = React.useState("all");
  const creatorsQ = useCreators(creators);
  const productsQ = useProducts(undefined, products);
  const { fetchNextPage, hasNextPage, isFetchingNextPage } = creatorsQ;
  const cList = creatorsQ.data ?? creators;
  const pList = productsQ.data ?? products;
  const isError = (creatorsQ.isError && !creatorsQ.data) || (productsQ.isError && !productsQ.data);
  const shown = cat === "all" ? cList : cList.filter((c) => c.category === cat);

  // 선반용 파생 목록 — 인기(팔로워 desc) / 신규(역순) / 추천 상품.
  const popular = React.useMemo(() => [...cList].sort((a, b) => b.followers - a.followers), [cList]);
  const fresh = React.useMemo(() => [...cList].reverse(), [cList]);

  const goSearch = (q: string) => router.push(`/search?q=${encodeURIComponent(q)}`);

  if (isError) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <ErrorState
          onRetry={() => {
            creatorsQ.refetch();
            productsQ.refetch();
          }}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8">
      <section className="flex flex-col gap-4">
        <h1 className="text-headline text-on-surface">크리에이터 발견</h1>
        <CategoryIconRow items={CATEGORY_ICONS} onSelect={goSearch} />
      </section>

      {/* 인기 크리에이터 선반(#10) — 사회적 증거 메타 노출(#12). */}
      <Shelf
        title="이번 주 인기 크리에이터"
        description="지금 가장 주목받는 크리에이터를 만나보세요"
        action={
          <Link href="/creator" className="text-body-s text-primary hover:underline">
            더보기
          </Link>
        }
      >
        {popular.map((c) => (
          <CreatorThumbCard
            key={c.id}
            name={c.name}
            meta={creatorMeta(c)}
            accentColor={c.accentColor}
            href={`/creator/${c.handle}`}
            className="w-40"
          />
        ))}
      </Shelf>

      {/* 추천 상품 선반 — 추천 근거 라벨(#9). */}
      <Shelf
        title="회원님을 위한 추천 상품"
        description="팔로우한 취향을 바탕으로 골랐어요"
        action={
          <Link href="/store" className="text-body-s text-primary hover:underline">
            더보기
          </Link>
        }
      >
        {pList.map((p) => (
          <MonetizableItem
            key={p.id}
            type={p.type}
            title={p.title}
            price={`₩${p.price.toLocaleString("ko-KR")}`}
            meta={p.meta}
            onAction={() => router.push(`/store/${p.id}`)}
            className="w-56"
          />
        ))}
      </Shelf>

      {/* 신규 크리에이터 선반. */}
      <Shelf title="새로 합류한 크리에이터" description="갓 시작한 크리에이터를 응원해 주세요">
        {fresh.map((c) => (
          <CreatorThumbCard
            key={c.id}
            name={c.name}
            meta={creatorMeta(c)}
            accentColor={c.accentColor}
            href={`/creator/${c.handle}`}
            className="w-40"
          />
        ))}
      </Shelf>

      {/* 전체 둘러보기 — 카테고리 필터 + 고밀도 그리드. */}
      <section className="flex flex-col gap-4">
        <h2 className="text-title-l text-on-surface">전체 둘러보기</h2>
        <SegmentedControl options={CATS} value={cat} onValueChange={setCat} />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {shown.map((c) => (
            <CreatorThumbCard
              key={c.id}
              name={c.name}
              meta={creatorMeta(c)}
              accentColor={c.accentColor}
              href={`/creator/${c.handle}`}
            />
          ))}
        </div>
        {/* 더보기 — 커서 다음 페이지가 있을 때만(무한 쿼리). 카테고리 필터는 로드된 전체에 적용. */}
        {hasNextPage ? (
          <div className="flex justify-center">
            <Button variant="outline" onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
              {isFetchingNextPage ? "불러오는 중…" : "더보기"}
            </Button>
          </div>
        ) : null}
      </section>
    </div>
  );
}
