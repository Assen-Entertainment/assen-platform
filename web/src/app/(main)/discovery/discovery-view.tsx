"use client";
import * as React from "react";
import { SegmentedControl, CreatorThumbCard, MonetizableItem } from "@/components/ui";
import type { Creator, Product } from "@/lib/api";

const CATS = [
  { label: "전체", value: "all" },
  { label: "일러스트", value: "일러스트" },
  { label: "뮤직", value: "뮤직" },
  { label: "버튜버", value: "버튜버" },
];

function followers(n: number): string {
  return n >= 1000 ? (n / 1000).toFixed(1).replace(/\.0$/, "") + "k" : String(n);
}

export function DiscoveryView({ creators, products }: { creators: Creator[]; products: Product[] }) {
  const [cat, setCat] = React.useState("all");
  const shown = cat === "all" ? creators : creators.filter((c) => c.category === cat);
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-10">
      <section className="flex flex-col gap-4">
        <h1 className="text-headline text-on-surface">크리에이터 발견</h1>
        <SegmentedControl options={CATS} value={cat} onValueChange={setCat} />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {shown.map((c) => (
            <CreatorThumbCard
              key={c.id}
              name={c.name}
              meta={`${c.category ?? ""} · 팔로워 ${followers(c.followers)}`}
              accentColor={c.accentColor}
              href={`/creator/${c.handle}`}
            />
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-title-l text-on-surface">지금 뜨는 아이템</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {products.map((p) => (
            <MonetizableItem key={p.id} type={p.type} title={p.title} price={`₩${p.price.toLocaleString("ko-KR")}`} meta={p.meta} />
          ))}
        </div>
      </section>
    </div>
  );
}
