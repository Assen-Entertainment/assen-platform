/**
 * 세션 만료(401) 전역 이벤트 — 뮤테이션이 인증 실패했을 때 UI 계층(토스트·리다이렉트)으로
 * 알리는 얇은 브로커. QueryProvider의 MutationCache가 emit하고, SessionGuard가 구독한다.
 * (훅 밖 컨텍스트에서 toast/router를 호출할 수 없어 이벤트로 우회한다.)
 */
type Handler = () => void;

let handler: Handler | null = null;

/** 401 핸들러 등록 — 반환된 함수로 해제. 마지막 등록자만 유효(단일 구독). */
export function onUnauthorized(next: Handler): () => void {
  handler = next;
  return () => {
    if (handler === next) handler = null;
  };
}

/** 401 발생 통지 — 등록된 핸들러가 있으면 호출(없으면 무시). */
export function emitUnauthorized(): void {
  handler?.();
}
