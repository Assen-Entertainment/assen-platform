import Link from "next/link";
import { Card, CardBody, Button, ListItem, Divider, StatItem, SectionHeader } from "@/components/ui";
import { STUDIO_RECENT } from "@/lib/studio-mock";

/** 대시보드 요약 지표(placeholder 수치 — 실 데이터 B2 게이트). */
const STATS: { label: string; value: string; delta: string; trend: "up" | "down" | "flat" }[] = [
  { label: "팔로워", value: "12,400", delta: "+3.2%", trend: "up" },
  { label: "이번 달 수익", value: "₩1,840,000", delta: "+12%", trend: "up" },
  { label: "신규 구독", value: "86", delta: "+9", trend: "up" },
  { label: "포스트 조회", value: "54,200", delta: "+5%", trend: "up" },
];

/** 서브메뉴 카드 — 스튜디오 각 영역 진입점. */
const SECTIONS = [
  { title: "상품 관리", desc: "굿즈·디지털·티켓 판매 관리", href: "/studio/products" },
  { title: "멤버십", desc: "티어·혜택 편집", href: "/studio/membership" },
  { title: "정산", desc: "수익·정산 내역", href: "/studio/settlement" },
  { title: "애널리틱스", desc: "구독자·수익 추이", href: "/studio/analytics" },
];

/** Creator Studio — 대시보드(통계 + 최근 + 서브메뉴). E4 / W3 개선. */
export default function StudioPage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-headline text-on-surface">크리에이터 스튜디오</h1>
        <Button asChild>
          <Link href="/studio/posts/new">새 포스트</Link>
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4 rounded-lg border border-outline bg-surface p-4 lg:grid-cols-4">
        {STATS.map((s) => (
          <StatItem key={s.label} label={s.label} value={s.value} delta={s.delta} trend={s.trend} />
        ))}
      </div>

      <section className="flex flex-col gap-3">
        <SectionHeader title="바로가기" description="스튜디오 주요 영역으로 이동" />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {SECTIONS.map((s) => (
            <Card key={s.href} className="transition-colors hover:bg-surface-container-high">
              <Link href={s.href} className="block">
                <CardBody className="flex-row items-center justify-between gap-3">
                  <div className="flex min-w-0 flex-col">
                    <span className="text-title-m text-on-surface">{s.title}</span>
                    <span className="text-body-s text-on-surface-variant">{s.desc}</span>
                  </div>
                  <span aria-hidden className="text-on-surface-variant">→</span>
                </CardBody>
              </Link>
            </Card>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <SectionHeader title="최근 항목" />
        <div className="overflow-hidden rounded-lg border border-outline">
          {STUDIO_RECENT.map((r, i) => (
            <div key={r.title}>
              {i > 0 ? <Divider /> : null}
              <Link href={r.href} className="block transition-colors hover:bg-surface-container-high">
                <ListItem title={r.title} subtitle={r.meta} showChevron />
              </Link>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
