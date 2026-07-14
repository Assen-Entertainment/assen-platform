/**
 * 분석 이벤트 카탈로그(ASS-203/ASS-170) — 도메인 이벤트의 타입드 정의.
 *
 * ★PII 금지 원칙: payload는 **식별자(id)·카운트·불리언·통제된 enum만** 담는다.
 *   전화번호·이름·주소·이메일·닉네임·검색어 원문·신고 서술 등 자유 텍스트/개인정보는 절대 포함하지 않는다
 *   (검색은 길이만, 신고는 유형 코드만). 각 payload를 좁은 타입으로 고정해 자유 문자열 필드를 최소화한다.
 */

/** 인증 방식 — 실 OTP("otp") / 소셜 OAuth("social") / 오프라인·데모 mock("mock"). PII 아님. */
export type AuthMethod = "otp" | "mock" | "social";

/**
 * 이벤트명 → payload 타입 매핑(단일 정본). 새 이벤트는 여기 한 곳에만 추가한다.
 * 값 타입은 string(식별자/enum)·number(카운트)·boolean만 허용(PII·자유 텍스트 금지).
 */
export interface AnalyticsEventMap {
  /** 라우트 변경(페이지 조회). path는 경로만(쿼리스트링 제외 — 검색어 등 PII 유입 차단). */
  page_view: { path: string };
  /** 회원가입 완료. */
  signup_completed: { method: AuthMethod };
  /** 로그인 완료. */
  login_completed: { method: AuthMethod };
  /** 팔로우 토글(팔로우/언팔로우). */
  follow_toggled: { following: boolean };
  /** 포스트 좋아요 토글. */
  post_liked: { liked: boolean };
  /** 댓글 작성 완료. */
  comment_created: { postId: string };
  /** 주문 생성(mock 결제 확정). 배송지 등 PII는 담지 않는다 — 상품 id·수량만. */
  order_created: { productId: string; qty: number };
  /** 구독 시작. */
  subscription_started: { tierId: string };
  /** 구독 티어 전환. */
  tier_changed: { tierId: string };
  /** 검색 실행(커밋). 검색어 원문 대신 길이만(PII·자유 텍스트 차단). */
  search_performed: { queryLength: number };
  /** 콘텐츠 신고 접수. 서술(narrative)은 제외 — 유형 코드만. */
  report_submitted: { reportType: string };
  /** 크리에이터 차단 토글(차단/해제). */
  block_toggled: { blocked: boolean };
}

/** 이벤트명 유니온. */
export type AnalyticsEventName = keyof AnalyticsEventMap;

/** 태그드 유니온 — 수집기가 소비하는 이벤트 형태({ name, props }). */
export type AnalyticsEvent = {
  [K in AnalyticsEventName]: { name: K; props: AnalyticsEventMap[K] };
}[AnalyticsEventName];
