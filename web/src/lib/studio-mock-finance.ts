// 스튜디오 재무 mock — ASS-289(#5). 정산/수익/수수료/원천징수 수치는 전부 placeholder 이며
// 실제 정산 규정이 아니다(대표·재무·법무 게이트 — 단독 확정 금지).
//
// ★번들 격리(ASS-289): 이 모듈의 런타임 데이터(SETTLEMENT_ROWS·ANALYTICS_SERIES)는 오직
// lib/api/index.ts의 getSettlementDemoRows/getAnalyticsDemoSeries(USE_API=false 폴백 분기)에서만
// 참조된다. 라이브 빌드(NEXT_PUBLIC_API_URL 설정)에선 lib/api가 mock/data.ts와 동일한 규율로
// USE_API 데드코드 분기를 접어 이 모듈을 트리셰이킹한다 → 날조 금액이 라이브 산출물(.next)에서
// 사라진다. 페이지/차트는 타입만 import(런타임 소거) 하므로 이 데이터를 번들에 붙들지 않는다.

export interface SettlementRow {
  id: string;
  period: string;
  /** 총 판매액(placeholder). */
  gross: number;
  /** 플랫폼 수수료(placeholder 율 — 확정 아님). */
  fee: number;
  /** 원천징수(placeholder — 세무 확정 아님). */
  withholding: number;
  /** 실지급액(placeholder). */
  net: number;
  status: "paid" | "scheduled" | "processing";
}

export const SETTLEMENT_ROWS: SettlementRow[] = [
  { id: "s1", period: "2026-06", gross: 1840000, fee: 184000, withholding: 60720, net: 1595280, status: "scheduled" },
  { id: "s2", period: "2026-05", gross: 1620000, fee: 162000, withholding: 53460, net: 1404540, status: "paid" },
  { id: "s3", period: "2026-04", gross: 1490000, fee: 149000, withholding: 49170, net: 1291830, status: "paid" },
  { id: "s4", period: "2026-03", gross: 1305000, fee: 130500, withholding: 43065, net: 1131435, status: "paid" },
];

export interface AnalyticsPoint {
  label: string;
  subscribers: number;
  revenue: number;
}

/** 6개월 시계열(placeholder). 차트 데모용. */
export const ANALYTICS_SERIES: AnalyticsPoint[] = [
  { label: "1월", subscribers: 620, revenue: 1180000 },
  { label: "2월", subscribers: 690, revenue: 1305000 },
  { label: "3월", subscribers: 742, revenue: 1490000 },
  { label: "4월", subscribers: 805, revenue: 1620000 },
  { label: "5월", subscribers: 861, revenue: 1720000 },
  { label: "6월", subscribers: 872, revenue: 1840000 },
];
