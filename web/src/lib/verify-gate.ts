// 본인인증 게이트 이벤트 버스 — 프레임워크 프리 모듈 싱글턴.
//  React 컴포넌트 트리 밖(QueryProvider의 MutationCache)에서도 호출 가능해야 하므로, 훅이 아닌
//  순수 모듈 함수로 구현한다. 미인증 팬이 게이트 상호작용(팔로우·구독·구매 등)을 시도해 서버가
//  403(IdentityVerificationRequired)을 내면 MutationCache가 emitVerifyRequired()로 신호하고,
//  VerifyGate 다이얼로그가 subscribeVerifyRequired로 구독해 뜬다.
const listeners = new Set<() => void>();

/** 본인인증 필요 신호 방출 — 구독 중인 모든 리스너를 호출한다. */
export function emitVerifyRequired(): void {
  listeners.forEach((l) => l());
}

/** 신호 구독 등록 → 해제 함수 반환(언마운트 시 호출). */
export function subscribeVerifyRequired(cb: () => void): () => void {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}
