import { describe, it, expect } from "vitest";
import { hasCoda, waGwa } from "./korean";

describe("korean 조사 헬퍼", () => {
  it("받침 유무를 판별한다", () => {
    expect(hasCoda("토끼방송국")).toBe(true); // 국(ㄱ 받침)
    expect(hasCoda("별빛 일러스트")).toBe(false); // 트(받침 없음)
    expect(hasCoda("묘화가")).toBe(false); // 가(받침 없음)
    expect(hasCoda("별빛")).toBe(true); // 빛(ㅊ 받침)
  });

  it("한글이 아니면 받침 없음으로 처리한다", () => {
    expect(hasCoda("Neon Beats")).toBe(false);
    expect(hasCoda("")).toBe(false);
  });

  it("와/과를 받침에 맞춰 고른다", () => {
    expect(waGwa("별빛 일러스트")).toBe("와");
    expect(waGwa("토끼방송국")).toBe("과");
    expect(waGwa("Neon Beats")).toBe("와");
  });
});
