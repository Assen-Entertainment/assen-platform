import * as React from "react";

/**
 * GateNote — 게이트 노트 노출 스위치(R5-W3 #4).
 * "(문구 placeholder — 법무 확정 전)" 류 내부 검증용 괄호 주석이 데모에서 그대로 노출되던 문제 해소.
 * 기본 off(프로덕션 데모엔 숨김). NEXT_PUBLIC_SHOW_GATE_NOTES=1|true 일 때만 렌더(내부 검증용).
 * ※법적 실문구(환불정책 실 내용·"법적 효력 없음" 초안 고지 등)는 이 스위치로 숨기지 않는다 — 오직 괄호/메타 주석만.
 */
export const SHOW_GATE_NOTES =
  process.env.NEXT_PUBLIC_SHOW_GATE_NOTES === "1" || process.env.NEXT_PUBLIC_SHOW_GATE_NOTES === "true";

export interface GateNoteProps {
  /** 래핑 태그(인라인=span 기본 / 블록=p). */
  as?: "span" | "p";
  children: React.ReactNode;
  className?: string;
}

export function GateNote({ as: As = "span", children, className }: GateNoteProps) {
  if (!SHOW_GATE_NOTES) return null;
  return <As className={className}>{children}</As>;
}
