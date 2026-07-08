"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import { SearchField, SegmentedControl, CreatorThumbCard, MonetizableItem, ErrorState, EmptyState, Skeleton } from "@/components/ui";
import { SearchIcon } from "@/lib/icons";
import { useSearch } from "@/lib/api/queries";
import { Stagger, StaggerItem } from "@/components/motion/motion-primitives";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { track } from "@/lib/analytics";
import type { Creator, Product } from "@/lib/api";

const RECENT_KEY = "assen.recentSearches";
const RECENT_MAX = 5;
const SUGGEST_LIMIT = 3;

/** 서제스트 옵션 — 최근 검색어 / 크리에이터 / 상품 / 전체 결과 보기(키보드 내비 대상). */
type Suggestion =
  | { kind: "recent"; term: string }
  | { kind: "creator"; creator: Creator }
  | { kind: "product"; product: Product }
  | { kind: "all"; term: string };

/** 검색 뷰 — 빈 질의=서버 제공 목록(브라우즈), 질의 시 B2 `/search` 소비(mock 폴백 동일 의미론). */
export function SearchView({
  creators,
  products,
  initialQuery = "",
}: {
  creators: Creator[];
  products: Product[];
  initialQuery?: string;
}) {
  const router = useRouter();
  const [q, setQ] = React.useState(initialQuery);
  const [tab, setTab] = React.useState("all");
  const qTrim = q.trim();
  // 서제스트·전체 결과 공용 — 타이핑 중간 요청 억제(250ms 디바운스).
  const debouncedQ = useDebouncedValue(qTrim, 250);
  const search = useSearch(debouncedQ);
  const active = debouncedQ.length > 0;
  const cl = active ? (search.data?.creators ?? []) : creators;
  const pl = active ? (search.data?.products ?? []) : products;
  const showError = active && search.isError && !search.data;

  // --- 서제스트 드롭다운(combobox) 상태 ---
  const [open, setOpen] = React.useState(false);
  const [highlight, setHighlight] = React.useState(-1);
  const [recent, setRecent] = React.useState<string[]>([]);

  // 최근 검색어 복원(마운트 후 — SSR 불일치 방지). 저장 실패(프라이빗 모드)는 in-memory 동작.
  React.useEffect(() => {
    try {
      const raw = localStorage.getItem(RECENT_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) setRecent(parsed.filter((t): t is string => typeof t === "string").slice(0, RECENT_MAX));
      }
    } catch {
      /* 접근 불가 무시 */
    }
  }, []);

  const persistRecent = React.useCallback((next: string[]) => {
    setRecent(next);
    try {
      localStorage.setItem(RECENT_KEY, JSON.stringify(next));
    } catch {
      /* 저장 실패 무시 */
    }
  }, []);
  const addRecent = React.useCallback(
    (term: string) => {
      const t = term.trim();
      if (!t) return;
      persistRecent([t, ...recent.filter((r) => r !== t)].slice(0, RECENT_MAX));
    },
    [recent, persistRecent],
  );
  const removeRecent = React.useCallback(
    (term: string) => persistRecent(recent.filter((r) => r !== term)),
    [recent, persistRecent],
  );

  const recentMode = qTrim.length === 0;

  // 키보드 내비 대상(평탄) — 최근 모드는 최근 검색어, 질의 모드는 서제스트(크리에이터·상품 각 3) + "전체 결과 보기".
  const options = React.useMemo<Suggestion[]>(() => {
    if (recentMode) return recent.map((term) => ({ kind: "recent", term }));
    const sugCreators = (search.data?.creators ?? []).slice(0, SUGGEST_LIMIT);
    const sugProducts = (search.data?.products ?? []).slice(0, SUGGEST_LIMIT);
    return [
      ...sugCreators.map((creator) => ({ kind: "creator", creator }) as const),
      ...sugProducts.map((product) => ({ kind: "product", product }) as const),
      { kind: "all", term: qTrim } as const,
    ];
  }, [recentMode, recent, search.data, qTrim]);

  // 질의 변경 시 하이라이트 초기화(엉뚱한 항목 실행 방지).
  React.useEffect(() => setHighlight(-1), [debouncedQ]);

  const showDropdown = open && ((recentMode && recent.length > 0) || !recentMode);

  const runSearch = (term: string) => {
    const t = term.trim();
    if (!t) return;
    addRecent(t);
    setOpen(false);
    setHighlight(-1);
    // 검색어 원문은 담지 않는다(PII·자유 텍스트 차단) — 길이만 계측.
    track("search_performed", { queryLength: t.length });
    router.push(`/search?q=${encodeURIComponent(t)}`);
  };
  const goto = (href: string) => {
    addRecent(qTrim);
    setOpen(false);
    setHighlight(-1);
    router.push(href);
  };
  const selectOption = (opt: Suggestion) => {
    if (opt.kind === "recent") runSearch(opt.term);
    else if (opt.kind === "creator") goto(`/creator/${opt.creator.handle}`);
    else if (opt.kind === "product") goto(`/store/${opt.product.id}`);
    else runSearch(opt.term);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setHighlight((h) => Math.min(h + 1, options.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, -1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (highlight >= 0 && options[highlight]) selectOption(options[highlight]);
      else runSearch(qTrim);
    } else if (e.key === "Escape") {
      setOpen(false);
      setHighlight(-1);
    }
  };

  const listboxId = "search-suggest-list";
  const optionId = (i: number) => `search-suggest-opt-${i}`;

  // iOS Safari: 드롭다운 옵션을 탭하면 input의 blur가 click보다 먼저 발생해 드롭다운이 닫히며 탭이
  // 유실된다. 옵션에서 pointerdown 기본동작(포커스 이동)을 막아 blur→닫힘을 차단(표준 해법).
  const preventBlur = (e: React.PointerEvent) => e.preventDefault();

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      {/* 검색 컨트롤 — 웜 캔버스 위에 뜬 surface 카드로 회색-온-회색 대비 문제 해소(#6). */}
      <div className="flex flex-col gap-4 rounded-xl border border-outline bg-surface p-4 shadow-1 sm:p-5">
      {/* combobox — 입력 포커스 시 서제스트/최근 검색어 드롭다운. 포커스가 래퍼 밖으로 나가면 닫힘.
          (래퍼 div는 포커스 경계용 onBlur만 — 상호작용은 내부 input[role=combobox]가 담당). */}
      {/* eslint-disable-next-line jsx-a11y/no-static-element-interactions */}
      <div
        className="relative"
        onBlur={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
            setOpen(false);
            setHighlight(-1);
          }
        }}
      >
        <SearchField
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder="크리에이터·상품 검색"
          aria-label="검색"
          role="combobox"
          aria-expanded={showDropdown}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={highlight >= 0 ? optionId(highlight) : undefined}
        />
        {showDropdown ? (
          <ul
            id={listboxId}
            role="listbox"
            aria-label="검색 제안"
            className="absolute inset-x-0 top-full z-50 mt-2 max-h-80 overflow-auto rounded-lg border border-outline bg-surface p-1 shadow-2"
          >
            {recentMode ? (
              <>
                <li className="flex items-center justify-between px-3 py-1.5 text-caption text-on-surface-variant">
                  <span>최근 검색어</span>
                  <button
                    type="button"
                    className="rounded px-1 text-caption text-on-surface-variant hover:text-on-surface"
                    onClick={() => persistRecent([])}
                    onPointerDown={preventBlur}
                  >
                    전체 삭제
                  </button>
                </li>
                {recent.map((term, i) => (
                  // role=presentation: 옵션(role=option)은 내부 select 버튼이 담당하고, 삭제 버튼은
                  // 옵션 밖(형제)에 둔다 — role=option 안에 인터랙티브 요소를 넣지 않는 리스트박스 패턴.
                  <li key={term} role="presentation" className={cnRow(highlight === i)}>
                    <button
                      type="button"
                      id={optionId(i)}
                      role="option"
                      aria-selected={highlight === i}
                      className="flex min-w-0 flex-1 items-center gap-2 text-left"
                      onMouseEnter={() => setHighlight(i)}
                      onClick={() => runSearch(term)}
                      onPointerDown={preventBlur}
                    >
                      <SearchIcon aria-hidden className="size-4 shrink-0 text-on-surface-variant" />
                      <span className="truncate text-body-m text-on-surface">{term}</span>
                    </button>
                    <button
                      type="button"
                      aria-label={`${term} 삭제`}
                      className="shrink-0 rounded px-1.5 text-on-surface-variant hover:text-error"
                      onClick={() => removeRecent(term)}
                      onPointerDown={preventBlur}
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </>
            ) : (
              <>
                {options.map((opt, i) =>
                  opt.kind === "creator" ? (
                    <li
                      key={`c-${opt.creator.id}`}
                      id={optionId(i)}
                      role="option"
                      aria-selected={highlight === i}
                      className={cnRow(highlight === i)}
                    >
                      <button
                        type="button"
                        className="flex min-w-0 flex-1 items-center gap-2 text-left"
                        onMouseEnter={() => setHighlight(i)}
                        onClick={() => selectOption(opt)}
                        onPointerDown={preventBlur}
                      >
                        <span
                          aria-hidden
                          className="size-6 shrink-0 rounded-full"
                          style={{ background: opt.creator.accentColor ?? "var(--color-surface-container-high)" }}
                        />
                        <span className="truncate text-body-m text-on-surface">{opt.creator.name}</span>
                        {opt.creator.category ? (
                          <span className="shrink-0 text-caption text-on-surface-variant">{opt.creator.category}</span>
                        ) : null}
                      </button>
                    </li>
                  ) : opt.kind === "product" ? (
                    <li
                      key={`p-${opt.product.id}`}
                      id={optionId(i)}
                      role="option"
                      aria-selected={highlight === i}
                      className={cnRow(highlight === i)}
                    >
                      <button
                        type="button"
                        className="flex min-w-0 flex-1 items-center justify-between gap-2 text-left"
                        onMouseEnter={() => setHighlight(i)}
                        onClick={() => selectOption(opt)}
                        onPointerDown={preventBlur}
                      >
                        <span className="truncate text-body-m text-on-surface">{opt.product.title}</span>
                        <span className="shrink-0 text-caption tabular-nums text-on-surface-variant">
                          ₩{opt.product.price.toLocaleString("ko-KR")}
                        </span>
                      </button>
                    </li>
                  ) : (
                    <li
                      key="all"
                      id={optionId(i)}
                      role="option"
                      aria-selected={highlight === i}
                      className={cnRow(highlight === i)}
                    >
                      <button
                        type="button"
                        className="flex w-full items-center gap-2 text-left"
                        onMouseEnter={() => setHighlight(i)}
                        onClick={() => selectOption(opt)}
                        onPointerDown={preventBlur}
                      >
                        <SearchIcon aria-hidden className="size-4 shrink-0 text-primary" />
                        <span className="truncate text-body-m text-primary">
                          &lsquo;{qTrim}&rsquo; 전체 결과 보기
                        </span>
                      </button>
                    </li>
                  ),
                )}
              </>
            )}
          </ul>
        ) : null}
      </div>
        <SegmentedControl
          options={[{ label: "전체", value: "all" }, { label: "크리에이터", value: "c" }, { label: "상품", value: "p" }]}
          value={tab}
          onValueChange={setTab}
        />
      </div>

      {/* 결과 컨텍스트(#6) — 질의 + 카운트로 텍스트 위계를 세운다. 빈 질의(브라우즈)는 안내 카피. */}
      {active && !showError && !(search.isFetching && !search.data) ? (
        <p className="px-0.5 text-body-s text-on-surface-variant">
          <span className="font-semibold text-on-surface">&lsquo;{qTrim}&rsquo;</span> 검색 결과 · 크리에이터{" "}
          <span className="tabular-nums text-on-surface">{cl.length}</span> · 상품{" "}
          <span className="tabular-nums text-on-surface">{pl.length}</span>
        </p>
      ) : !active ? (
        <p className="px-0.5 text-body-s text-on-surface-variant">지금 주목받는 크리에이터와 상품을 둘러보세요</p>
      ) : null}

      {showError ? (
        <ErrorState onRetry={() => search.refetch()} />
      ) : active && search.isFetching && !search.data ? (
        <SearchResultsSkeleton />
      ) : active && cl.length === 0 && pl.length === 0 ? (
        <EmptyState title="검색 결과가 없어요" description="다른 키워드로 검색하거나 철자를 확인해 보세요." />
      ) : (
        <>
          {(tab === "all" || tab === "c") && cl.length > 0 ? (
            <section className="flex flex-col gap-3">
              <h2 className="text-title-l text-on-surface">크리에이터</h2>
              <Stagger className="grid grid-cols-2 gap-4 sm:grid-cols-4" amount={0.08}>
                {cl.map((c) => (
                  <StaggerItem key={c.id} lift>
                    <CreatorThumbCard name={c.name} meta={c.category} accentColor={c.accentColor} href={`/creator/${c.handle}`} />
                  </StaggerItem>
                ))}
              </Stagger>
            </section>
          ) : null}
          {(tab === "all" || tab === "p") && pl.length > 0 ? (
            <section className="flex flex-col gap-3">
              <h2 className="text-title-l text-on-surface">상품</h2>
              <Stagger className="grid grid-cols-2 gap-4 sm:grid-cols-4" amount={0.08}>
                {pl.map((p) => (
                  <StaggerItem key={p.id} lift>
                    <MonetizableItem type={p.type} title={p.title} price={`₩${p.price.toLocaleString("ko-KR")}`} meta={p.meta} onAction={() => router.push(`/store/${p.id}`)} />
                  </StaggerItem>
                ))}
              </Stagger>
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}

/** 서제스트 옵션 행 클래스 — 하이라이트(키보드/호버) 시 강조 배경. */
function cnRow(highlighted: boolean): string {
  return `flex items-center gap-1 rounded-sm px-3 py-2 ${highlighted ? "bg-surface-container-high" : ""}`;
}

/** 검색 로딩 스켈레톤(#6) — 질의 결과를 받아오는 동안 빈 화면 대신 카드 자리표시(reduced-motion 시 정적). */
function SearchResultsSkeleton() {
  return (
    <section className="flex flex-col gap-3" aria-hidden>
      <Skeleton className="h-6 w-28" />
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="flex flex-col gap-2">
            <Skeleton className="aspect-square w-full rounded-lg" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        ))}
      </div>
    </section>
  );
}
