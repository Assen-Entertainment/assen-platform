import {
  StatItem,
  DataTable,
  type DataTableColumn,
  Badge,
  SectionHeader,
  DisclaimerNotice,
  SafetyGuideNotice,
  EmptyState,
  SHOW_GATE_NOTES,
} from "@/components/ui";
import { ChartBarLineIcon } from "@/components/ui/empty-state-icons";
import { won } from "@/lib/studio-mock";
import { getSettlementDemoRows, type SettlementRow } from "@/lib/api";

// 상태 라벨 매핑(재무 수치 아님 — 지급완료/예정/처리중). 데모·라이브 공통 presentational 상수.
const SETTLEMENT_STATUS_META: Record<SettlementRow["status"], { label: string; variant: "success" | "neutral" | "warning" }> = {
  paid: { label: "지급완료", variant: "success" },
  scheduled: { label: "지급예정", variant: "neutral" },
  processing: { label: "처리중", variant: "warning" },
};

const columns: DataTableColumn<SettlementRow>[] = [
  { key: "period", header: "정산 월" },
  { key: "gross", header: "총 판매액", align: "right", render: (r) => <span className="tabular-nums">{won(r.gross)}</span> },
  { key: "fee", header: "수수료", align: "right", render: (r) => <span className="tabular-nums text-on-surface-variant">-{won(r.fee)}</span> },
  {
    key: "withholding",
    header: "원천징수",
    align: "right",
    render: (r) => <span className="tabular-nums text-on-surface-variant">-{won(r.withholding)}</span>,
  },
  { key: "net", header: "실지급액", align: "right", render: (r) => <span className="tabular-nums text-on-surface">{won(r.net)}</span> },
  {
    key: "status",
    header: "상태",
    render: (r) => {
      const m = SETTLEMENT_STATUS_META[r.status];
      return <Badge variant={m.variant}>{m.label}</Badge>;
    },
  },
];

/**
 * Studio 정산 — 오너 스코프 라우트(/studio/* 는 middleware 세션 가드). 정산 금액은 서버가 실제로
 * 제공할 때만 노출한다. getSettlementDemoRows는 라이브(USE_API)에서 null(서버 정산 계약 없음 →
 * 클라이언트가 금액을 날조하지 않음)을, mock 폴백에서만 데모 정산표를 반환한다. 라이브 빌드에선
 * 이 mock 데이터가 lib/api에서 트리셰이킹되어 날조 금액이 번들에 실리지 않는다(ASS-289 #5).
 */
export default function StudioSettlementPage() {
  const rows = getSettlementDemoRows();

  // 라이브: 정산 데이터 없음 → "준비 중" 안내(mock 금액 렌더 안 함). 빈 배열(스텁)도 동일 처리.
  if (!rows || rows.length === 0) {
    return (
      <div className="mx-auto flex max-w-5xl flex-col gap-5">
        <SectionHeader title="정산" description="수익과 정산 내역을 확인하세요" />
        <div className="rounded-lg border border-outline bg-surface p-4">
          <EmptyState
            icon={<ChartBarLineIcon />}
            title="정산 데이터 준비 중이에요"
            description="정산 내역은 준비되는 대로 이곳에 표시됩니다. 아직 표시할 정산 데이터가 없어요."
          />
        </div>
        <SafetyGuideNotice title="정산 투명성">
          모든 판매·수수료·지급 내역은 월 단위로 기록되어 언제든 확인할 수 있어요. 정산 관련 문의는 고객센터를 통해
          접수하면 영업일 기준으로 답변드립니다.
        </SafetyGuideNotice>
      </div>
    );
  }

  const latest = rows[0];
  // rows는 mock 경로에서 항상 비지 않은 배열이라 실질적으로 발생하지 않는 방어 가드.
  if (!latest) return null;
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-5">
      <SectionHeader title="정산" description="데모 데이터 — 수익과 정산 내역 미리보기" />

      <div className="grid grid-cols-1 gap-4 rounded-lg border border-outline bg-surface p-4 sm:grid-cols-3">
        {/* note(괄호/메타 주석)는 게이트 스위치로만 노출(#4). 실 고지는 아래 DisclaimerNotice가 항상 담당. */}
        <StatItem label="이번 달 수익" value={won(latest.gross)} note={SHOW_GATE_NOTES ? "※ placeholder — 확정 아님" : undefined} />
        <StatItem label="정산 예정액" value={won(latest.net)} note={SHOW_GATE_NOTES ? "※ placeholder — 확정 아님" : undefined} />
        <StatItem label="공제 합계 (수수료+원천징수)" value={won(latest.fee + latest.withholding)} note={SHOW_GATE_NOTES ? "※ 요율 미확정(게이트)" : undefined} />
      </div>

      <DisclaimerNotice title="정산 수치 안내 (데모)">
        표시된 수수료율·원천징수·정산 주기는 데모용 placeholder 이며 확정된 정책이 아닙니다. 실제 요율과 지급 조건은
        재무·법무 검토 후 별도 공지됩니다.
      </DisclaimerNotice>

      <div className="flex flex-col gap-2">
        <SectionHeader as="h3" title="정산 내역 (데모)" />
        <DataTable columns={columns} rows={rows} rowKey={(r) => r.id} caption="월별 정산 내역 (데모 데이터)" />
      </div>

      <SafetyGuideNotice title="정산 투명성">
        모든 판매·수수료·지급 내역은 월 단위로 기록되어 언제든 확인할 수 있어요. 정산 관련 문의는 고객센터를 통해 접수하면
        영업일 기준으로 답변드립니다.
      </SafetyGuideNotice>
    </div>
  );
}
