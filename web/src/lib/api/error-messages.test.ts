import { describe, it, expect } from "vitest";
import { ApiError } from "./client";
import { apiErrorMessage, ERROR_CODE_MESSAGES, ERROR_CODES } from "./error-messages";

/**
 * error code 소비(R4-W1) — 서버 `{detail, code}`에서 code 기반 분기·문구 일원화.
 * 우선순위: fallbackMap[code] → ERROR_CODE_MESSAGES[code] → detail → fallback.
 */
describe("apiErrorMessage (code→한국어 매핑)", () => {
  it("code를 기본 매핑으로 변환한다(detail보다 우선)", () => {
    const e = new ApiError(422, "x", "서버 상세 문구", "OutOfStock");
    expect(apiErrorMessage(e)).toBe(ERROR_CODE_MESSAGES.OutOfStock);
  });

  it("fallbackMap이 기본 매핑을 오버라이드한다", () => {
    const e = new ApiError(422, "x", "서버 상세", "OutOfStock");
    expect(apiErrorMessage(e, { OutOfStock: "이 뷰 특화 문구" })).toBe("이 뷰 특화 문구");
  });

  it("매핑에 없는 code는 서버 detail(표시용)로 폴백한다", () => {
    const e = new ApiError(422, "x", "서버가 준 상세", "UnmappedCode");
    expect(apiErrorMessage(e)).toBe("서버가 준 상세");
  });

  it("code가 없으면 detail → 최후 폴백 순으로 내려간다", () => {
    expect(apiErrorMessage(new ApiError(500, "x", "상세만 있음"))).toBe("상세만 있음");
    expect(apiErrorMessage(new ApiError(500, "x"))).toBe("잠시 후 다시 시도해 주세요.");
    expect(apiErrorMessage(new ApiError(500, "x"), undefined, "커스텀 폴백")).toBe("커스텀 폴백");
  });

  it("ApiError가 아니면 곧바로 폴백을 반환한다", () => {
    expect(apiErrorMessage(new Error("boom"))).toBe("잠시 후 다시 시도해 주세요.");
    expect(apiErrorMessage("nope", undefined, "폴백")).toBe("폴백");
  });

  it("ERROR_CODES 미러 상수는 값=키로 안정 식별자를 노출하고 문구 매핑과 일원화된다(로그인 매직스트링 제거)", () => {
    // 로그인 뷰가 참조하는 code(매직스트링 대신 상수).
    expect(ERROR_CODES.AccountNotRegistered).toBe("AccountNotRegistered");
    expect(ERROR_CODES.OtpInvalid).toBe("OtpInvalid");
    // 모든 미러 상수는 값=키이며 문구 매핑에도 존재(단일 출처 일관성).
    for (const [key, value] of Object.entries(ERROR_CODES)) {
      expect(value).toBe(key);
      expect(ERROR_CODE_MESSAGES[value]).toBeTruthy();
    }
  });

  it("계약표의 주요 code가 모두 매핑돼 있다", () => {
    for (const code of [
      "AccountNotRegistered",
      "OtpInvalid",
      "ProductNotOrderable",
      "OutOfStock",
      "MembershipOnlyProduct",
      "DuplicateSubscription",
      "OrderNotCancellable",
      "TierInUse",
      "PaymentCardInvalid",
      "PaymentMethodNotFound",
    ]) {
      expect(ERROR_CODE_MESSAGES[code]).toBeTruthy();
    }
  });
});
