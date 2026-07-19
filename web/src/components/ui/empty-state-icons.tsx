import * as React from "react";

/**
 * 빈 상태 전용 라인 아이콘 세트 — 미니멀 럭셔리 아웃라인.
 * 앱 아웃라인 아이콘 패밀리와 동일 톤: stroke 1.5 · round cap/join · currentColor 상속.
 * 자체완결 SVG(외부 에셋 0). 크기·색은 EmptyState 원판이 지정한다([&>svg]:size-6 · text-on-surface-variant).
 * 각 컨텍스트 시맨틱:
 *  주문=영수증 · 구독/멤버십=하트카드 · 차단=금지(슬래시 서클) · 상품=박스 · 정산=막대차트
 *  · 애널리틱스=추이선 · 최근활동=펄스 · 검색/필터빈=돋보기 · 결제=카드 · 기본 폴백=수신함.
 * 생 이모지(🚫 등) 전면 대체용 — 플랫폼 의존 렌더를 제거하고 다크/라이트 모두 동일하게 읽힌다.
 */
export type EmptyStateIconProps = React.SVGProps<SVGSVGElement>;

/** 공통 라인 아이콘 셸 — 스트로크 웨이트·캡·조인을 한 규격으로 고정. */
function LineIcon({ children, ...props }: EmptyStateIconProps & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      {...props}
    >
      {children}
    </svg>
  );
}

/** 수신함 — 기본 폴백(아이콘 미지정 EmptyState). 알림·피드 등 범용 빈 상태에도 자연스럽다. */
export function InboxLineIcon(props: EmptyStateIconProps) {
  return (
    <LineIcon {...props}>
      <path d="M22 12h-6l-2 3h-4l-2-3H2" />
      <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
    </LineIcon>
  );
}

/** 영수증 — 주문 내역. 톱니 밑변 + 항목 라인. */
export function ReceiptLineIcon(props: EmptyStateIconProps) {
  return (
    <LineIcon {...props}>
      <path d="M6 3h12v17l-2-1.2-2 1.2-2-1.2-2 1.2-2-1.2-2 1.2z" />
      <path d="M9 8h6" />
      <path d="M9 11.5h6" />
      <path d="M9 15h3.5" />
    </LineIcon>
  );
}

/** 멤버십 카드 + 하트 — 구독. 좋아요 하트와 달리 카드에 얹혀 "멤버십"을 전달. */
export function MembershipLineIcon(props: EmptyStateIconProps) {
  return (
    <LineIcon {...props}>
      <path d="M3.5 8A2.5 2.5 0 0 1 6 5.5h12A2.5 2.5 0 0 1 20.5 8v8a2.5 2.5 0 0 1-2.5 2.5H6A2.5 2.5 0 0 1 3.5 16z" />
      <path d="M12 15.3c-.9-.9-3.4-2.6-3.4-4.6 0-1.15.93-1.9 1.95-1.9.8 0 1.25.42 1.45.72.2-.3.65-.72 1.45-.72 1.02 0 1.95.75 1.95 1.9 0 2-2.5 3.7-3.4 4.6z" />
    </LineIcon>
  );
}

/** 금지(슬래시 서클) — 차단. 라인 스타일 no-symbol. */
export function BlockLineIcon(props: EmptyStateIconProps) {
  return (
    <LineIcon {...props}>
      <circle cx="12" cy="12" r="8" />
      <path d="m6.4 6.4 11.2 11.2" />
    </LineIcon>
  );
}

/** 박스(패키지) — 상품. */
export function BoxLineIcon(props: EmptyStateIconProps) {
  return (
    <LineIcon {...props}>
      <path d="m7.5 4.27 9 5.15" />
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      <path d="M3.3 7 12 12l8.7-5" />
      <path d="M12 22V12" />
    </LineIcon>
  );
}

/** 막대 차트 — 정산. 축 + 상승 막대 3개. */
export function ChartBarLineIcon(props: EmptyStateIconProps) {
  return (
    <LineIcon {...props}>
      <path d="M4 4v16h16" />
      <rect x="6.8" y="14" width="2.6" height="6" rx="0.6" />
      <rect x="10.9" y="11" width="2.6" height="9" rx="0.6" />
      <rect x="15" y="8" width="2.6" height="12" rx="0.6" />
    </LineIcon>
  );
}

/** 추이선 — 애널리틱스. 축 + 상승 라인(막대와 구분). */
export function TrendLineIcon(props: EmptyStateIconProps) {
  return (
    <LineIcon {...props}>
      <path d="M4 4v16h16" />
      <path d="m7 15.5 3.3-4 3 2.4L20 7.5" />
    </LineIcon>
  );
}

/** 펄스 — 최근 활동. */
export function ActivityLineIcon(props: EmptyStateIconProps) {
  return (
    <LineIcon {...props}>
      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
    </LineIcon>
  );
}

/** 돋보기 — 검색·필터 결과 없음(스토어 필터빈 등). */
export function SearchLineIcon(props: EmptyStateIconProps) {
  return (
    <LineIcon {...props}>
      <circle cx="11" cy="11" r="7" />
      <path d="m20.5 20.5-4.3-4.3" />
    </LineIcon>
  );
}

/** 카드 — 결제 수단. */
export function CardLineIcon(props: EmptyStateIconProps) {
  return (
    <LineIcon {...props}>
      <rect x="3" y="5" width="18" height="14" rx="2.5" />
      <path d="M3 9.5h18" />
      <path d="M6.5 14.5h4" />
    </LineIcon>
  );
}
