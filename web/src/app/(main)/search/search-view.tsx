"use client";
import * as React from "react";
import { SearchField, SegmentedControl, CreatorThumbCard, MonetizableItem } from "@/components/ui";
import type { Creator, Product } from "@/lib/api";

export function SearchView({ creators, products }: { creators: Creator[]; products: Product[] }) {
  const [q, setQ] = React.useState("");
  const [tab, setTab] = React.useState("all");
  const cl = creators.filter((c) => c.name.toLowerCase().includes(q.toLowerCase()));
  const pl = products.filter((p) => p.title.toLowerCase().includes(q.toLowerCase()));
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
