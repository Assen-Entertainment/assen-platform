import { describe, it, expect } from "vitest";
import { reduceToastQueue, MAX_TOASTS } from "./use-toast";

/** R5-W3 #2 — 토스트 큐 정책(상한·중복 병합) 순수 함수 검증. */
describe("reduceToastQueue", () => {
  it("동시 개수를 MAX_TOASTS로 제한하고 초과 시 가장 오래된 것을 제거한다", () => {
    let items: { id: number; title?: string; description?: string }[] = [];
    for (let i = 1; i <= 5; i++) {
      items = reduceToastQueue(items, { title: `t${i}` }, i);
    }
    expect(items).toHaveLength(MAX_TOASTS);
    // 최신 3개만 남는다(t3, t4, t5).
    expect(items.map((i) => i.title)).toEqual(["t3", "t4", "t5"]);
    // 오래된 id(1,2)는 제거됨.
    expect(items.map((i) => i.id)).toEqual([3, 4, 5]);
  });

  it("title+description이 모두 같으면 새로 쌓지 않고 마지막 항목을 새 id로 교체(병합·타이머 리셋)", () => {
    let items = reduceToastQueue([], { title: "저장됨", description: "완료" }, 1);
    items = reduceToastQueue(items, { title: "저장됨", description: "완료" }, 2);
    // 병합 — 1개만 유지, 최신 내용/새 id.
    expect(items).toHaveLength(1);
    expect(items[0]).toEqual({ id: 2, title: "저장됨", description: "완료" });
  });

  it("title이 같아도 description이 다르면 병합하지 않는다(내용 유실 방지)", () => {
    let items = reduceToastQueue([], { title: "저장됨", description: "1회" }, 1);
    items = reduceToastQueue(items, { title: "저장됨", description: "2회" }, 2);
    // 서로 다른 내용 — 둘 다 유지(2회차 안내가 1회차를 삼키지 않음).
    expect(items).toHaveLength(2);
    expect(items.map((i) => i.description)).toEqual(["1회", "2회"]);
  });

  it("직전과 다른 title은 병합하지 않고 append 한다", () => {
    let items = reduceToastQueue([], { title: "A" }, 1);
    items = reduceToastQueue(items, { title: "B" }, 2);
    expect(items.map((i) => i.title)).toEqual(["A", "B"]);
  });

  it("연속 중복 후 다른 title, 다시 중복 — 병합은 직전 항목만 대상", () => {
    let items = reduceToastQueue([], { title: "A" }, 1);
    items = reduceToastQueue(items, { title: "A" }, 2); // 병합 → [A(2)]
    items = reduceToastQueue(items, { title: "B" }, 3); // append → [A(2), B(3)]
    items = reduceToastQueue(items, { title: "A" }, 4); // 직전이 B라 병합 안 함 → [A(2), B(3), A(4)]
    expect(items.map((i) => i.title)).toEqual(["A", "B", "A"]);
    expect(items).toHaveLength(3);
  });

  it("updater는 멱등 — 같은 prev/id로 두 번 호출해도 결과가 같다(strict-mode 이중 호출 안전)", () => {
    const prev = [{ id: 1, title: "A" }];
    const once = reduceToastQueue(prev, { title: "B" }, 2);
    const twice = reduceToastQueue(prev, { title: "B" }, 2);
    expect(once).toEqual(twice);
  });
});
