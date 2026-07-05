/**
 * 알림 읽음 전역 이벤트 — 읽음 뮤테이션(useMarkNotificationRead/All)이 실시간 뱃지 소스
 * (useNotificationSocket)에 읽음을 통지하는 얇은 브로커(session-events와 동일 패턴).
 *
 * 소켓은 서버 authoritative `unread_count`(+푸시 증가)를 유지하되, 읽음 성공 시 이 이벤트로 뱃지를
 * 감소/재동기해 스테일-하이(읽었는데 뱃지가 안 줄어듦)를 막는다. 훅 밖에서 setState를 직접 호출할 수
 * 없어 이벤트로 우회한다. 소켓 비활성(WS 미설정) 시 구독자가 없어 emit은 no-op → 회귀 0.
 */
type ReadEvent = { type: "one" } | { type: "all" };
type Handler = (e: ReadEvent) => void;

let handler: Handler | null = null;

/** 읽음 이벤트 핸들러 등록 — 반환된 함수로 해제. 마지막 등록자만 유효(단일 구독·셸 1회 마운트). */
export function onNotificationsRead(next: Handler): () => void {
  handler = next;
  return () => {
    if (handler === next) handler = null;
  };
}

/** 단건 읽음 통지 — 뱃지 1 감소(구독자 없으면 무시). */
export function emitNotificationRead(): void {
  handler?.({ type: "one" });
}

/** 모두 읽음 통지 — 뱃지 0으로 재동기(구독자 없으면 무시). */
export function emitAllNotificationsRead(): void {
  handler?.({ type: "all" });
}
