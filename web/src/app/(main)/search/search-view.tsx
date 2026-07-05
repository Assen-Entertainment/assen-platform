"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import { SearchField, SegmentedControl, CreatorThumbCard, MonetizableItem, ErrorState, EmptyState } from "@/components/ui";
import { SearchIcon } from "@/lib/icons";
import { useSearch } from "@/lib/api/queries";
import { useDebouncedValue } from "@/lib/use-debounced-value";
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

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
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
                  >
                    전체 삭제
                  </button>
                </li>
                {recent.map((term, i) => (
                  <li
                    key={term}
                    id={optionId(i)}
                    role="option"
                    aria-selected={highlight === i}
                    className={cnRow(highlight === i)}
                  >
                    <button
                      type="button"
                      className="flex min-w-0 flex-1 items-center gap-2 text-left"
                      onMouseEnter={() => setHighlight(i)}
                      onClick={() => runSearch(term)}
                    >
                      <SearchIcon aria-hidden className="size-4 shrink-0 text-on-surface-variant" />
                      <span className="truncate text-body-m text-on-surface">{term}</span>
                    </button>
                    <button
                      type="button"
                      aria-label={`${term} 삭제`}
                      className="shrink-0 rounded px-1.5 text-on-surface-variant hover:text-error"
                      onClick={() => removeRecent(term)}
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
      {showError ? (
        <ErrorState onRetry={() => search.refetch()} />
      ) : active && cl.length === 0 && pl.length === 0 ? (
        <EmptyState title="검색 결과가 없어요" description="다른 키워드로 검색하거나 철자를 확인해 보세요." />
      ) : (
        <>
          {(tab === "all" || tab === "c") && cl.length > 0 ? (
            <section className="flex flex-col gap-3">
              <h2 className="text-title-l text-on-surface">크리에이터</h2>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                {cl.map((c) => (
                  <CreatorThumbCard key={c.id} name={c.name} meta={c.category} accentColor={c.accentColor} href={`/creator/${c.handle}`} />
                ))}
              </div>
            </section>
          ) : null}
          {(tab === "all" || tab === "p") && pl.length > 0 ? (
            <section className="flex flex-col gap-3">
              <h2 className="text-title-l text-on-surface">상품</h2>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                {pl.map((p) => (
                  <MonetizableItem key={p.id} type={p.type} title={p.title} price={`₩${p.price.toLocaleString("ko-KR")}`} meta={p.meta} onAction={() => router.push(`/store/${p.id}`)} />
                ))}
              </div>
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
