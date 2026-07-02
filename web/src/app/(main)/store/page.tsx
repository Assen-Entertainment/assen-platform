"use client";
import * as React from "react";
import { Chip, MonetizableItem, type MonetizableItemType } from "@/components/ui";

const FILTERS = ["전체", "굿즈", "디지털", "체험", "티켓"] as const;

const ALL: { type: MonetizableItemType; cat: string; title: string; price: string; meta: string }[] = [
  { type: "goods", cat: "굿즈", title: "아크릴 스탠드", price: "₩18,000", meta: "한정 200개" },
  { type: "goods", cat: "굿즈", title: "엔러지 키링", price: "₩9,000", meta: "재고 53개" },
  { type: "digital", cat: "디지털", title: "고해상도 화보집", price: "₩9,900", meta: "다운로드" },
  { type: "digital", cat: "디지털", title: "라이브 월페이퍼 팩", price: "₩4,500", meta: "다운로드" },
  { type: "experience", cat: "체험", title: "포토카드 팬사인", price: "₩30,000", meta: "선착순 20" },
  { type: "experience", cat: "체험", title: "그림 첨삭", price: "₩20,000", meta: "주 5명" },
  { type: "ticket", cat: "티켓", title: "온라인 팬미팅", price: "₩25,000", meta: "12/24 20:00" },
  { type: "coupon", cat: "굿즈", title: "10% 할인 쿠폰", price: "₩3,000", meta: "30일 유효" },
];

export default function StorePage() {
  const [f, setF] = React.useState<(typeof FILTERS)[number]>("전체");
  const items = f === "전체" ? ALL : ALL.filter((i) => i.cat === f);
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <h1 className="text-headline text-on-surface">스토어</h1>
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((x) => (
          <Chip key={x} selected={f === x} onClick={() => setF(x)}>
            {x}
          </Chip>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {items.map((it) => (
          <MonetizableItem key={it.title} type={it.type} title={it.title} price={it.price} meta={it.meta} />
        ))}
      </div>
    </div>
  );
}
