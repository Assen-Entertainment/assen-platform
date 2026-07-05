// 로그인 복귀(next) + 미완료 액션 재실행 브리지.
//  • sanitizeNext: ?next= 오픈 리다이렉트 방어 — 동일 오리진 상대경로만 허용.
//  • PendingAction: 비로그인 상태에서 시도한 액션(팔로우)을 sessionStorage에 잠시 보관해
//    로그인 성공 후 원경로로 복귀했을 때 자동 재실행한다. (좋아요·구독은 후속 — union 확장)

/** 복귀 실패 시 안전한 기본 경로(사이트 첫인상). */
export const DEFAULT_NEXT = "/discovery";

/**
 * ?next= 값을 안전한 내부 경로로 강제한다(오픈 리다이렉트 방어).
 * 허용: 단일 "/"로 시작하는 상대경로. 거부(→ 기본값): 절대 URL·스킴, "//"(프로토콜 상대),
 * 백슬래시(브라우저가 "/"로 정규화해 "//" 우회), 제어문자.
 */
export function sanitizeNext(raw: string | null | undefined): string {
  if (!raw || typeof raw !== "string") return DEFAULT_NEXT;
  if (!raw.startsWith("/")) return DEFAULT_NEXT; // 절대 URL·스킴 거부
  if (raw.startsWith("//")) return DEFAULT_NEXT; // 프로토콜 상대 URL 거부
  if (raw.includes("\\")) return DEFAULT_NEXT; // 백슬래시(브라우저가 / 로 정규화) 거부
  // 제어문자(개행·NUL 등) 삽입 우회 차단 — charCode < 0x20.
  for (let i = 0; i < raw.length; i += 1) {
    if (raw.charCodeAt(i) < 0x20) return DEFAULT_NEXT;
  }
  return raw;
}

/** 로그인 후 재실행할 미완료 액션. 현재는 팔로우만(구조는 union으로 확장 가능). */
export type PendingAction = { action: "follow"; handle: string; from: string };

const PENDING_KEY = "assen.pendingAction";

/** 미완료 액션 저장(sessionStorage — 탭 세션 한정, 새로고침 견딤·탭 닫으면 소거). */
export function savePendingAction(a: PendingAction): void {
  try {
    sessionStorage.setItem(PENDING_KEY, JSON.stringify(a));
  } catch {
    /* 저장 실패 무시(프라이빗 모드 등) */
  }
}

/** 미완료 액션 읽기 — 형태 검증 통과분만 반환(손상값은 null). */
export function readPendingAction(): PendingAction | null {
  try {
    const raw = sessionStorage.getItem(PENDING_KEY);
    if (!raw) return null;
    const p = JSON.parse(raw) as Partial<PendingAction>;
    if (p && p.action === "follow" && typeof p.handle === "string" && typeof p.from === "string") {
      return { action: "follow", handle: p.handle, from: p.from };
    }
  } catch {
    /* 파싱 실패 무시 */
  }
  return null;
}

/** 미완료 액션 제거(재실행 후·만료 시). */
export function clearPendingAction(): void {
  try {
    sessionStorage.removeItem(PENDING_KEY);
  } catch {
    /* 제거 실패 무시 */
  }
}
