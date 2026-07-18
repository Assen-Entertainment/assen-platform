import * as Sentry from "@sentry/nextjs";

/**
 * 서버/엣지 Sentry 초기화(ASS-270) — Next.js 15 `register()` 훅.
 *
 * env-gated no-op: `SENTRY_DSN` 미설정이면 init 자체를 호출하지 않는다. 서버 Django
 * 쪽 `config/observability.py`의 `init_sentry()`(SENTRY_DSN 없으면 완전 no-op) 계약과
 * 동일한 원칙 — dev/test/미설정 배포는 네트워크·성능 영향이 0이다.
 */
const dsn = process.env.SENTRY_DSN;
const rawSampleRate = Number.parseFloat(process.env.SENTRY_TRACES_SAMPLE_RATE ?? "0.1");
const tracesSampleRate = Number.isFinite(rawSampleRate) ? rawSampleRate : 0.1;

export async function register() {
  if (!dsn) return;

  Sentry.init({
    dsn,
    environment: process.env.SENTRY_ENVIRONMENT || process.env.NODE_ENV,
    // 보수적 기본값(0.1) — env로 튜닝 가능. 트레이싱은 기본 off가 아니라 절제된 샘플링.
    tracesSampleRate,
    // 서버 스크러버(observability.py)와 정합 — 쿠키/IP/요청 바디 등 기본 PII를 캡처하지 않는다.
    sendDefaultPii: false,
  });
}

// Next.js `onRequestError` 훅 — DSN 미설정 시 `Sentry.init`이 호출되지 않아 활성 클라이언트가
// 없으므로 `captureRequestError`는 안전하게 아무 것도 하지 않는다(Sentry SDK 표준 동작 —
// 클라이언트 부재 시 capture* 계열 함수는 조용히 no-op).
export const onRequestError = Sentry.captureRequestError;
