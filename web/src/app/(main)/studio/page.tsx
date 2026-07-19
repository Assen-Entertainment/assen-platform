import Link from "next/link";
import { Card, CardBody, Button, EmptyState, SectionHeader } from "@/components/ui";
import { ActivityLineIcon } from "@/components/ui/empty-state-icons";
import { StudioStatsGrid } from "./studio-stats";

/** 서브메뉴 카드 — 스튜디오 각 영역 진입점. */
const SECTIONS = [
  { title: "포스트 관리", desc: "발행한 포스트 수정·삭제", href: "/studio/posts" },
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

      {/* 실 카운트 대시보드(R4-W5) — GET /studio/stats 소비. 수익 카드 없음(정산 게이트). */}
      <StudioStatsGrid />

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
        <div className="overflow-hidden rounded-lg border border-outline bg-surface">
          <EmptyState
            icon={<ActivityLineIcon />}
            title="아직 최근 활동이 없어요"
            description="포스트·상품·멤버십 활동이 쌓이면 여기에 표시돼요."
          />
        </div>
      </section>
    </div>
  );
}
