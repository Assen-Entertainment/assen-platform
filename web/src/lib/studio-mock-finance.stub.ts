/**
 * 스튜디오 재무 mock 스텁(ASS-289 #5 번들 격리) — 라이브 빌드(NEXT_PUBLIC_API_URL 설정) 전용 웹팩 치환 타깃.
 *
 * ★배경: lib/api의 `USE_API` 분기는 빌드타임 상수이지만, 측정 결과(라이브 빌드 grep) SWC 미니파이어가
 * 각 getter의 mock 폴백 `return`문까지는 사병(dead-code) 제거하지 못한다(mock/data.ts와 동일 현상 —
 * data.stub.ts 주석 참조). 따라서 next.config.mjs의 NormalModuleReplacementPlugin이 라이브 빌드에서
 * `@/lib/studio-mock-finance`(실 placeholder 금액)를 이 빈 스텁으로 **물리 치환**해 확정적으로 제거한다.
 *
 * ★안전성: USE_API=true 런타임 경로는 lib/api의 getSettlementDemoRows/getAnalyticsDemoSeries가
 * 이 값들을 읽기 전에 null을 반환하므로(if(USE_API) 분기가 먼저 return) 빈 값 대체에 의미론적 회귀가 없다.
 * dev(mock 빌드)·vitest는 이 파일을 참조하지 않는다(웹팩 프로덕션 빌드 전용 치환 — 실 데이터 정본은 ./studio-mock-finance).
 */
export interface SettlementRow {
  id: string;
  period: string;
  gross: number;
  fee: number;
  withholding: number;
  net: number;
  status: "paid" | "scheduled" | "processing";
}
export interface AnalyticsPoint {
  label: string;
  subscribers: number;
  revenue: number;
}
export const SETTLEMENT_ROWS: SettlementRow[] = [];
export const ANALYTICS_SERIES: AnalyticsPoint[] = [];

/**
 * 타입 패리티 가드 — emit 되지 않는 타입 전용 검사(런타임 무영향). 이 스텁의 값 export 시그니처가
 * 실 모듈과 어긋나면(누락·타입 드리프트) tsc 가 실패한다(data.stub.ts와 동일 규율).
 */
type _AssertAssignable<A extends B, B> = A extends B ? true : never;
type _StubMirrorsReal = _AssertAssignable<
  typeof import("./studio-mock-finance.stub"),
  typeof import("./studio-mock-finance")
>;
