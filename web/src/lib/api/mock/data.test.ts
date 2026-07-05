import { describe, it, expect } from "vitest";
import * as mock from "./data";
import { mockSetBlocked as reexported } from "../index";

/**
 * mock 격리 모듈(R6-W2C) — import 경로/재노출 계약. 값은 기존 in-file mock과 동일(회귀 0),
 * index는 mockSetBlocked를 "./index" 경로로 재노출해 기존 소비처(queries.ts·테스트) 경로가 안정.
 */
describe("mock/data 격리 모듈", () => {
  it("mock 데이터 배열을 그대로 노출한다(값 이동만 — 회귀 0)", () => {
    expect(mock.CREATORS).toHaveLength(5);
    expect(mock.PRODUCTS).toHaveLength(9);
    expect(mock.ORDERS).toHaveLength(3);
    expect(mock.CREATORS[0].name).toBe("별빛 일러스트");
    expect(mock.ORDERS[0].id).toBe("ASN-1024");
  });

  it("index 재노출 mockSetBlocked는 격리 모듈과 동일 참조·동일 MOCK_BLOCKED 상태를 공유한다", () => {
    expect(reexported).toBe(mock.mockSetBlocked);
    reexported("c1", true);
    expect(mock.MOCK_BLOCKED.has("c1")).toBe(true);
    reexported("c1", false);
    expect(mock.MOCK_BLOCKED.has("c1")).toBe(false);
  });
});
