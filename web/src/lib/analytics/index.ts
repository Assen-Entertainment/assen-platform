/**
 * 분석 계측 파사드(ASS-203/ASS-170) — `track(name, props)` 단일 진입점 + 수집기(Collector) 추상화.
 *
 * 설계:
 *  • 기본 no-op — 등록된 수집기가 없으면 아무 일도 안 한다(프로덕션 수집기는 나중에 env로 꽂는다).
 *  • 다중 수집기 등록 가능(registerCollector). NEXT_PUBLIC_ANALYTICS_DEBUG=1이면 console 수집기 자동 등록.
 *  • SSR 안전 — 서버 렌더(typeof window === "undefined")에선 track이 no-op(클라 전용).
 *  • 수집기 예외가 앱 흐름을 막지 않는다(try/catch 격리).
 *
 * 계측 지점은 한 곳으로 일원화한다(중복 발화 금지):
 *  뮤테이션 이벤트=queries.ts onSuccess, 인증=session.tsx, 검색=search-view, page_view=route tracker 1곳.
 */
import type { AnalyticsEvent, AnalyticsEventMap, AnalyticsEventName } from "./events";

export type { AnalyticsEvent, AnalyticsEventMap, AnalyticsEventName, AuthMethod } from "./events";

/** 수집기 인터페이스 — 이벤트를 실제 목적지(console·프로덕션 SDK 등)로 보낸다. */
export interface AnalyticsCollector {
  collect(event: AnalyticsEvent): void;
}

// 모듈 스코프 레지스트리(클라 단일 인스턴스). 기본 비어 있음 → track은 no-op.
const collectors: AnalyticsCollector[] = [];

/** 수집기 등록 → 해제 함수 반환(useEffect cleanup 용). */
export function registerCollector(collector: AnalyticsCollector): () => void {
  collectors.push(collector);
  return () => {
    const i = collectors.indexOf(collector);
    if (i >= 0) collectors.splice(i, 1);
  };
}

let defaultsReady = false;

/** 등록된 수집기·기본 등록 플래그 초기화(테스트/HMR 용). */
export function resetCollectors(): void {
  collectors.length = 0;
  defaultsReady = false;
}

/** 디버그 수집기 — 이벤트를 console.debug로 관찰(개발/스테이징 자리표시, 프로덕션 SDK 이전). */
export function createConsoleCollector(): AnalyticsCollector {
  return {
    collect(event) {
      console.debug("[analytics]", event.name, event.props);
    },
  };
}

/**
 * 기본 수집기 등록(멱등·클라 전용) — NEXT_PUBLIC_ANALYTICS_DEBUG=1이면 console 수집기를 1회 등록한다.
 * 프로덕션 수집기는 이 자리에서 env 플래그로 추가 배선한다(현재는 no-op 기본).
 */
export function initAnalytics(): void {
  if (defaultsReady || typeof window === "undefined") return;
  defaultsReady = true;
  if (process.env.NEXT_PUBLIC_ANALYTICS_DEBUG === "1") {
    registerCollector(createConsoleCollector());
  }
}

/**
 * 이벤트 발화 — 등록된 모든 수집기에 전달. 타입드(name↔props 계약 강제).
 * SSR·수집기 부재 시 no-op. 수집기 예외는 삼켜 앱 흐름을 보호한다.
 */
export function track<K extends AnalyticsEventName>(name: K, props: AnalyticsEventMap[K]): void {
  if (typeof window === "undefined") return; // 클라 전용 가드(SSR no-op)
  if (collectors.length === 0) return;
  const event = { name, props } as AnalyticsEvent;
  for (const collector of collectors) {
    try {
      collector.collect(event);
    } catch {
      /* 수집기 오류 격리 — 계측이 앱을 깨뜨리지 않는다 */
    }
  }
}
