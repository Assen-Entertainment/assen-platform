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
import { useSession } from "@/lib/session";
import { useInfiniteScroll } from "@/lib/use-infinite-scroll";
import { Reveal, Stagger, StaggerItem } from "@/components/motion/motion-primitives";
import { Spinner } from "@/components/ui";
import type { Creator, Page, Product } from "@/lib/api";

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

export function DiscoveryView({ creators, products }: { creators: Page<Creator>; products: Page<Product> }) {
  const router = useRouter();
  const { user } = useSession();
  const [cat, setCat] = React.useState("all");
  const creatorsQ = useCreators(creators);
  const productsQ = useProducts(undefined, products);
  const { fetchNextPage, hasNextPage, isFetchingNextPage } = creatorsQ;
  const cList = creatorsQ.data ?? creators.items;
  const pList = productsQ.data ?? products.items;
  const isError = (creatorsQ.isError && !creatorsQ.data) || (productsQ.isError && !productsQ.data);
  const shown = cat === "all" ? cList : cList.filter((c) => c.category === cat);

  // 무한 스크롤(전체 둘러보기 그리드) — sentinel 근접 시 크리에이터 다음 페이지 자동 로드.
  const sentinelRef = React.useRef<HTMLDivElement>(null);
  const canLoadMore = hasNextPage && !isFetchingNextPage;
  useInfiniteScroll(sentinelRef, {
    enabled: canLoadMore,
    onLoadMore: () => {
      if (canLoadMore) fetchNextPage();
    },
  });

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
      {/* 히어로 — 편집형 프론트도어(시그니처 gradient.brand 모먼트). 진입 시 살짝 떠오름(reduced-motion 가드). */}
      <section
        className="relative overflow-hidden rounded-xl px-6 py-10 [animation:fade-up_500ms_ease-out] sm:px-10 sm:py-12"
        style={{ backgroundImage: "var(--gradient-brand)" }}
      >
        <div aria-hidden className="pointer-events-none absolute -right-16 -top-24 size-64 rounded-full bg-white/10 blur-2xl" />
        <div aria-hidden className="pointer-events-none absolute -bottom-24 -left-10 size-56 rounded-full bg-white/10 blur-3xl" />
        {/* 브랜드 시그니처 워터마크 — Logo(app/icon.svg)와 형태를 공유하는 상승 "A" 봉우리. 우측 저채도. */}
        <svg
          aria-hidden
          viewBox="0 0 32 32"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="pointer-events-none absolute -right-6 top-1/2 hidden h-[150%] -translate-y-1/2 text-white/[0.08] sm:block"
        >
          <path d="M10 23 L16 8.5 L22 23 M12.6 17.6 H19.4" />
        </svg>
        {/* 대각 시트 하이라이트 — 광택감(깊이). */}
        <div aria-hidden className="pointer-events-none absolute inset-0 bg-gradient-to-tr from-white/10 via-transparent to-transparent" />
        {/* 좌측 다크 스크림 — 브랜드 그라디언트를 유지하면서 텍스트 대비 AA 보장. */}
        <div aria-hidden className="pointer-events-none absolute inset-0 bg-gradient-to-r from-black/25 via-black/5 to-transparent" />
        <div className="relative flex max-w-2xl flex-col gap-3 text-white">
          <span className="text-label font-semibold uppercase tracking-[0.16em] text-white/90">크리에이터 커머스</span>
          <h1 className="text-display-m font-bold leading-[1.15] tracking-tight text-white sm:text-display-xl">
            취향에 맞는 크리에이터를 발견하세요
          </h1>
          <p className="max-w-xl text-body-l text-white/90">
            팔로우부터 멤버십·굿즈까지, 크리에이터의 세계를 한 곳에서 만나보세요.
          </p>
        </div>
      </section>

      {/* 카테고리 탐색(#7) — 콜드스타트 진입점. */}
      <Reveal>
        <CategoryIconRow items={CATEGORY_ICONS} onSelect={goSearch} />
      </Reveal>

      {/* 인기 크리에이터 선반(#10) — 사회적 증거 메타 노출(#12). */}
      <Reveal>
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
      </Reveal>

      {/* 추천 상품 선반 — 개인화 카피는 로그인 시에만. 비로그인은 일반 카피(#9·P0 비로그인 동선). */}
      <Reveal>
        <Shelf
          title={user ? "회원님을 위한 추천 상품" : "지금 주목받는 상품"}
          description={user ? "팔로우한 취향을 바탕으로 골랐어요" : "많은 팬이 함께 보고 있는 상품이에요"}
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
      </Reveal>

      {/* 신규 크리에이터 선반. */}
      <Reveal>
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
      </Reveal>

      {/* 전체 둘러보기 — 카테고리 필터 + 고밀도 그리드. */}
      <section className="flex flex-col gap-4">
        <h2 className="text-title-l text-on-surface">전체 둘러보기</h2>
        <SegmentedControl options={CATS} value={cat} onValueChange={setCat} />
        {/* 스태거드 진입 + hover 리프트(#8) — 그리드 카드가 순차로 떠오르고, 커서 오버 시 살짝 뜬다. */}
        <Stagger className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5" amount={0.08}>
          {shown.map((c) => (
            <StaggerItem key={c.id} lift>
              <CreatorThumbCard
                name={c.name}
                meta={creatorMeta(c)}
                accentColor={c.accentColor}
                href={`/creator/${c.handle}`}
              />
            </StaggerItem>
          ))}
        </Stagger>
        {/* 무한 스크롤 sentinel + 폴백 버튼(카테고리 필터는 로드된 전체에 적용). */}
        {hasNextPage ? (
          <div className="flex flex-col items-center gap-3">
            <div ref={sentinelRef} aria-hidden className="h-px w-full" />
            {isFetchingNextPage ? <Spinner aria-label="더 불러오는 중" /> : null}
            <Button variant="outline" onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
              {isFetchingNextPage ? "불러오는 중…" : "더 불러오기"}
            </Button>
          </div>
        ) : null}
      </section>
    </div>
  );
}
