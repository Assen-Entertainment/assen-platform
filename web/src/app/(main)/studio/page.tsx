import Link from "next/link";
import { Card, CardBody, Button, ListItem, Divider } from "@/components/ui";

const STATS = [
  { label: "팔로워", value: "12,400", delta: "+3.2%" },
  { label: "이번 달 수익", value: "₩1,840,000", delta: "+12%" },
  { label: "신규 구독", value: "86", delta: "+9" },
  { label: "포스트 조회", value: "54,200", delta: "+5%" },
];

const RECENT = [
  { title: "신작 일러스트 공개", meta: "포스트 · 좋아요 842" },
  { title: "아크릴 스탠드", meta: "상품 · 판매 124" },
  { title: "스탠다드 멤버십", meta: "멤버십 · 구독 86" },
];

/** Creator Studio — 대시보드(통계 + 최근). E4. */
export default function StudioPage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-headline text-on-surface">크리에이터 스튜디오</h1>
        <Button asChild>
          <Link href="/post">새 포스트</Link>
        </Button>
      </div>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {STATS.map((s) => (
          <Card key={s.label}>
            <CardBody className="flex flex-col gap-1">
              <span className="text-body-s text-on-surface-variant">{s.label}</span>
              <span className="text-display-m text-on-surface">{s.value}</span>
              <span className="text-caption text-success">{s.delta}</span>
            </CardBody>
          </Card>
        ))}
      </div>
      <section className="flex flex-col gap-3">
        <h2 className="text-title-l text-on-surface">최근 항목</h2>
        <div className="overflow-hidden rounded-lg border border-outline">
          {RECENT.map((r, i) => (
            <div key={r.title}>
              {i > 0 ? <Divider /> : null}
              <ListItem title={r.title} subtitle={r.meta} showChevron />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
