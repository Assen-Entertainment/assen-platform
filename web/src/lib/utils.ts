import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/**
 * twMerge 커스텀 설정 — Assen 디자인 토큰 정합.
 *
 * 문제: 기본 twMerge는 커스텀 폰트 크기(`text-title-m`·`text-label` 등)와 커스텀 온컬러
 * (`text-on-primary`·`text-on-creator-accent` 등)를 모두 `text-color` 그룹의 캐치올 검증기로
 * 분류한다. 그 결과 한 요소에 크기 클래스와 색 클래스가 함께 오면(예: Button size=lg의
 * `text-title-m` + variant=primary의 `text-on-primary`) 뒤에 온 크기 클래스가 색 클래스를
 * 밀어내 온컬러가 사라진다 → primary/accent 버튼이 본문 색(on-surface)을 상속해 대비 불량.
 *
 * 해결: 커스텀 폰트 크기 토큰을 `font-size` 그룹에 리터럴로 등록한다. 리터럴 매칭이 캐치올
 * 검증기보다 우선하므로 `text-<size>`는 font-size로, `text-<color>`는 text-color로 분리 분류되어
 * 충돌하지 않는다(둘 다 보존). 토큰 목록은 styles/globals.css `@theme`의 --text-* 미러.
 */
const FONT_SIZES = [
  "display-xl",
  "display-l",
  "display-m",
  "headline",
  "title-l",
  "title-m",
  "body-l",
  "body-m",
  "body-s",
  "label",
  "caption",
] as const;

const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [{ text: [...FONT_SIZES] }],
    },
  },
});

/** Tailwind 클래스 병합 헬퍼 (조건부 + 충돌 해소). */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
