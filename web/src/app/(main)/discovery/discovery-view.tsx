"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Chip,
  Spinner,
  CreatorThumbCard,
  MonetizableItem,
  ErrorState,
  EmptyState,
  CategoryIconRow,
  Shelf,
  LoadMore,
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
import { CREATOR_CATEGORIES, categoryLabel } from "@/lib/creator-categories";
import { Reveal, Stagger, StaggerItem } from "@/components/motion/motion-primitives";
import { COVER_GRAIN_URI } from "@/lib/placeholder";
import type { Creator, Page, Product } from "@/lib/api";

// 전체 둘러보기 필터 — 정본 크리에이터 카테고리(CREATOR_CATEGORIES) 전부 + '전체'.
// 서버 필터(정확일치)와 값이 일치하고, 8개까지 늘어도 칩 행(줄바꿈)이라 오버플로/CLS가 없다.
const CATS = [
  { label: "전체", value: "all" },
  ...CREATOR_CATEGORIES.map((c) => ({ label: categoryLabel(c), value: c })),
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
  // 카테고리가 있을 때만 "카테고리 · " 접두 — 빈 카테고리에서 dangling 구분자(" · 팔로워")를 없앤다.
  const prefix = c.category ? `${categoryLabel(c.category)} · ` : "";
  return `${prefix}팔로워 ${followers(c.followers)}`;
}

export function DiscoveryView({
  creators,
  products,
  popularCreators,
  freshCreators,
}: {
  creators: Page<Creator>;
  products: Page<Product>;
  /** 서버 랭킹(sort=popular, E11) — 팔로워 desc 단일 페이지. */
  popularCreators: Page<Creator>;
  /** 서버 랭킹(sort=new, E11) — 최신 가입 desc 단일 페이지. */
  freshCreators: Page<Creator>;
}) {
  const router = useRouter();
  const [cat, setCat] = React.useState("all");
  const creatorsQ = useCreators(creators);
  const popularQ = useCreators(popularCreators, "popular");
  const freshQ = useCreators(freshCreators, "new");
  const productsQ = useProducts(undefined, products);
  const { fetchNextPage, hasNextPage, isFetchingNextPage } = creatorsQ;
  const cList = creatorsQ.data ?? creators.items;
  const pList = productsQ.data ?? products.items;
  const isError =
    (creatorsQ.isError && !creatorsQ.data) ||
    (productsQ.isError && !productsQ.data) ||
    (popularQ.isError && !popularQ.data) ||
    (freshQ.isError && !freshQ.data);
  const filtering = cat !== "all";
  const shown = filtering ? cList.filter((c) => c.category === cat) : cList;
  // 카테고리 필터는 클라에 로드된 목록에만 적용된다 — 여러 페이지면 뒤 페이지의 매칭이 누락되고,
  // 로드된 페이지에 매칭이 없으면 "없어요" 빈 상태와 "더보기"가 동시에 뜬다. 필터 활성 시 남은
  // 페이지를 모두 당겨 필터가 전체 집합을 보게 한다(store-view와 동일한 하드닝, 모순 제거).
  React.useEffect(() => {
    if (filtering && hasNextPage && !isFetchingNextPage) void fetchNextPage();
  }, [filtering, hasNextPage, isFetchingNextPage, fetchNextPage]);
  // 필터 집합이 아직 완성 전(더 당길 페이지 남음)이면 성급한 빈 상태 대신 로딩을 보여준다.
  const filteredIncomplete = filtering && hasNextPage;

  // 인기/신규 크리에이터 선반 — 서버 랭킹(sort=popular/new, E11) 소비(클라 sort/reverse 제거).
  const popular = popularQ.data ?? popularCreators.items;
  const fresh = freshQ.data ?? freshCreators.items;

  const goSearch = (q: string) => router.push(`/search?q=${encodeURIComponent(q)}`);

  if (isError) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <ErrorState
          onRetry={() => {
            creatorsQ.refetch();
            productsQ.refetch();
            popularQ.refetch();
            freshQ.refetch();
          }}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8">
      {/* 히어로 — 편집형 프론트도어(R14 미니멀 럭셔리). 채도 높은 풀 워시 대신 warm-paper surface 위에
          타이포그래피로 리드하고 브랜드 액센트는 절제해 씀(우상단 옅은 글로우 + 프라이머리 아이브로우).
          진입 시 살짝 떠오름(reduced-motion 은 globals 전역 가드로 축소). */}
      <section className="relative overflow-hidden rounded-xl border border-outline bg-surface px-6 py-14 [animation:fade-up_500ms_ease-out] sm:px-12 sm:py-20">
        {/* 절제된 브랜드 액센트 — 우상단 저채도 글로우(풀 워시 아님, color-mix 로 라이트/다크 추종). */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(90% 130% at 100% 0%, color-mix(in oklab, var(--primary) 10%, transparent) 0%, transparent 55%)",
          }}
        />
        {/* 초저강도 그레인 — "디자인된 종이" 질감(커버 폴백과 동일 텍스처로 시스템 일관성). */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.55] mix-blend-soft-light"
          style={{ backgroundImage: `url("${COVER_GRAIN_URI}")`, backgroundSize: "140px 140px" }}
        />
        <div className="relative flex max-w-2xl flex-col gap-5">
          {/* 아이브로우 — 한글은 uppercase 무의미 + 넓은 트래킹은 음절을 벌려 어색("크 리 에 이 터").
              아이브로우 감각은 weight + text-primary + 작은 크기로, 트래킹은 타이트하게. */}
          <span className="text-label font-semibold tracking-[0.02em] text-primary">크리에이터 커머스</span>
          <h1 className="text-balance text-[2rem] font-bold leading-[1.08] tracking-[-0.02em] text-on-surface sm:text-[2.75rem] lg:text-[3.25rem]">
            취향으로 이어지는
            <br className="hidden sm:block" /> 크리에이터의 세계
          </h1>
          <p className="max-w-lg text-pretty text-body-l text-on-surface-variant">
            팔로우부터 멤버십·굿즈까지, 좋아하는 크리에이터를 한 곳에서 만나고 응원하세요.
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

      {/*
        인기 상품 선반 — 서버 상품 추천 엔드포인트는 아직 없다(E11 sort=recommended는 크리에이터
        전용, 범위 밖 상품 추천 API 신설 대신 크리에이터 랭킹을 우선 배선했다 — 위 인기/신규 선반).
        그래서 이 선반은 일반 상품 목록(useProducts)을 그대로 노출한다 — 개인화 랭킹이 아니므로
        로그인 여부와 무관하게 논-퍼스널라이즈 카피를 쓴다(디자인 리뷰 F1: 과잉약속 카피 정직화).
      */}
      <Reveal>
        <Shelf
          title="인기 상품"
          description="지금 주목받는 상품들"
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
              mediaUrl={p.mediaUrl}
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
        <h2 className="text-balance text-title-l text-on-surface">전체 둘러보기</h2>
        {/* 카테고리 필터 — 정본 카테고리 칩 행(줄바꿈). 단일 선택(전체 = 필터 해제). */}
        <div className="flex flex-wrap gap-2" role="group" aria-label="카테고리 필터">
          {CATS.map((x) => (
            <Chip key={x.value} selected={cat === x.value} onClick={() => setCat(x.value)}>
              {x.label}
            </Chip>
          ))}
        </div>
        {/* 스태거드 진입 + hover 리프트(#8) — 그리드 카드가 순차로 떠오르고, 커서 오버 시 살짝 뜬다.
            카테고리 필터가 0건이면 빈 그리드 대신 안내(sparse 런치 blank body 방지). 단, 필터 집합이
            아직 완성 전(뒤 페이지 로드 중)이면 성급한 빈 상태 대신 스피너를 보인다. */}
        {shown.length === 0 ? (
          filteredIncomplete ? (
            <div className="flex justify-center py-12">
              <Spinner />
            </div>
          ) : (
            <EmptyState
              title="해당하는 크리에이터가 없어요"
              description="다른 카테고리를 선택해보세요."
            />
          )
        ) : (
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
        )}
        {/* 무한 스크롤은 '전체'에서만 — 필터 중엔 위 effect가 남은 페이지를 자동 로드하므로 수동 더보기를 숨긴다. */}
        {!filtering ? (
          <LoadMore
            hasNextPage={hasNextPage}
            isFetchingNextPage={isFetchingNextPage}
            onLoadMore={() => fetchNextPage()}
            itemCount={cList.length}
          />
        ) : null}
      </section>
    </div>
  );
}
