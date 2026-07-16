import { describe, it, expect, vi } from "vitest";
import { emitVerifyRequired, subscribeVerifyRequired } from "./verify-gate";

/**
 * 본인인증 게이트 이벤트 버스(B2) — 컴포넌트 트리 밖(MutationCache)에서 방출하는 신호를
 * 구독자(VerifyGate 다이얼로그)가 받는다. 구독/해제/다중 구독자 계약을 검증한다.
 */
describe("verify-gate event bus", () => {
  it("emit 시 구독한 리스너가 호출된다", () => {
    const cb = vi.fn();
    const off = subscribeVerifyRequired(cb);
    emitVerifyRequired();
    expect(cb).toHaveBeenCalledTimes(1);
    off();
  });

  it("해제(unsubscribe) 후에는 호출되지 않는다", () => {
    const cb = vi.fn();
    const off = subscribeVerifyRequired(cb);
    off();
    emitVerifyRequired();
    expect(cb).not.toHaveBeenCalled();
  });

  it("여러 구독자가 모두 호출된다", () => {
    const a = vi.fn();
    const b = vi.fn();
    const offA = subscribeVerifyRequired(a);
    const offB = subscribeVerifyRequired(b);
    emitVerifyRequired();
    expect(a).toHaveBeenCalledTimes(1);
    expect(b).toHaveBeenCalledTimes(1);
    offA();
    offB();
  });
});
