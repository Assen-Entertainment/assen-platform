"use client";
import * as React from "react";
import { SearchField, SegmentedControl, CreatorThumbCard, MonetizableItem } from "@/components/ui";
import { useSearch } from "@/lib/api/queries";
import type { Creator, Product } from "@/lib/api";

/** 검색 뷰 — 빈 질의=서버 제공 목록(브라우즈), 질의 시 B2 `/search` 소비(mock 폴백 동일 의미론). */
export function SearchView({ creators, products }: { creators: Creator[]; products: Product[] }) {
  const [q, setQ] = React.useState("");
  const [tab, setTab] = React.useState("all");
  const deferredQ = React.useDeferredValue(q.trim());
  const search = useSearch(deferredQ);
  const cl = deferredQ ? (search.data?.creators ?? []) : creators;
  const pl = deferredQ ? (search.data?.products ?? []) : products;
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <SearchField value={q} onChange={(e) => setQ(e.target.value)} placeholder="크리에이터·상품 검색" />
      <SegmentedControl
        options={[{ label: "전체", value: "all" }, { label: "크리에이터", value: "c" }, { label: "상품", value: "p" }]}
        value={tab}
        onValueChange={setTab}
      />
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
              <MonetizableItem key={p.id} type={p.type} title={p.title} price={`₩${p.price.toLocaleString("ko-KR")}`} meta={p.meta} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
