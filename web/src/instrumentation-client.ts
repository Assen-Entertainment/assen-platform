import * as Sentry from "@sentry/nextjs";

/**
 * 클라이언트 Sentry 초기화(ASS-270) — Next.js 15 클라이언트 계측 진입점(SDK v10 방식,
 * `sentry.client.config.ts`를 대체). 앱 하이드레이션 전에 로드된다.
 *
 * env-gated no-op: `NEXT_PUBLIC_SENTRY_DSN` 미설정이면 init을 호출하지 않는다 — 서버
 * `config/observability.py`의 no-op-without-DSN 계약과 동일 원칙(dev/test/미설정 배포는
 * 네트워크·성능 영향 0). SDK 코드 자체는 이 파일이 항상 로드되므로 번들에 포함되지만
 * (번들예산은 scripts/check-bundle-budget.mjs가 별도 검증), 런타임 init/네트워크는 스킵된다.
 */
const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  const rawSampleRate = Number.parseFloat(process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? "0.1");
  const tracesSampleRate = Number.isFinite(rawSampleRate) ? rawSampleRate : 0.1;

  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || process.env.NODE_ENV,
    // 보수적 기본값(0.1) — env로 튜닝 가능.
    tracesSampleRate,
    // 서버 스크러버(observability.py)와 정합 — 쿠키/IP 등 기본 PII를 캡처하지 않는다.
    sendDefaultPii: false,
  });
}

// App Router 내비게이션을 트레이스에 연결하는 훅(Sentry 권장 배선, next lint가 누락 시 경고).
// DSN 미설정 시 클라이언트가 없으므로 호출돼도 안전하게 아무 것도 하지 않는다(onRequestError와 동일 원칙).
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
