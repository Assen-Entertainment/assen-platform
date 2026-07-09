import {
  StatItem,
  DataTable,
  type DataTableColumn,
  Badge,
  SectionHeader,
  DisclaimerNotice,
  SafetyGuideNotice,
  SHOW_GATE_NOTES,
} from "@/components/ui";
import { SETTLEMENT_ROWS, SETTLEMENT_STATUS_META, won, type SettlementRow } from "@/lib/studio-mock";

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
 * Studio 정산 — Figma Web-Settlement(185:273) / W3.
 * 요약 StatItem + 정산 내역 DataTable + 투명성 안내.
 * ※수수료율·원천징수·정산 주기 수치는 전부 placeholder(재무·법무·대표 게이트 — 단독 확정 금지).
 */
export default function StudioSettlementPage() {
  const latest = SETTLEMENT_ROWS[0];
  // SETTLEMENT_ROWS는 항상 비지 않은 정적 mock 배열이라 실질적으로 발생하지 않는 방어 가드.
  if (!latest) return null;
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-5">
      <SectionHeader title="정산" description="수익과 정산 내역을 확인하세요" />

      <div className="grid grid-cols-1 gap-4 rounded-lg border border-outline bg-surface p-4 sm:grid-cols-3">
        {/* note(괄호/메타 주석)는 게이트 스위치로만 노출(#4). 실 고지는 아래 DisclaimerNotice가 항상 담당. */}
        <StatItem label="이번 달 수익" value={won(latest.gross)} note={SHOW_GATE_NOTES ? "※ placeholder — 확정 아님" : undefined} />
        <StatItem label="정산 예정액" value={won(latest.net)} note={SHOW_GATE_NOTES ? "※ placeholder — 확정 아님" : undefined} />
        <StatItem label="공제 합계 (수수료+원천징수)" value={won(latest.fee + latest.withholding)} note={SHOW_GATE_NOTES ? "※ 요율 미확정(게이트)" : undefined} />
      </div>

      <DisclaimerNotice title="정산 수치 안내">
        표시된 수수료율·원천징수·정산 주기는 데모용 placeholder 이며 확정된 정책이 아닙니다. 실제 요율과 지급 조건은
        재무·법무 검토 후 별도 공지됩니다.
      </DisclaimerNotice>

      <div className="flex flex-col gap-2">
        <SectionHeader as="h3" title="정산 내역" />
        <DataTable columns={columns} rows={SETTLEMENT_ROWS} rowKey={(r) => r.id} caption="월별 정산 내역" />
      </div>

      <SafetyGuideNotice title="정산 투명성">
        모든 판매·수수료·지급 내역은 월 단위로 기록되어 언제든 확인할 수 있어요. 정산 관련 문의는 고객센터를 통해 접수하면
        영업일 기준으로 답변드립니다.
      </SafetyGuideNotice>
    </div>
  );
}
