import { describe, it, expect, afterEach, vi } from "vitest";
import { render } from "@testing-library/react";

/**
 * R5-W3 #4 — GateNote 노출 스위치. SHOW_GATE_NOTES는 모듈 로드 시 env를 읽으므로
 * stubEnv → resetModules → dynamic import 순서로 각 분기를 검증한다.
 */
afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

async function loadGateNote(value?: string) {
  vi.resetModules();
  if (value === undefined) vi.stubEnv("NEXT_PUBLIC_SHOW_GATE_NOTES", "");
  else vi.stubEnv("NEXT_PUBLIC_SHOW_GATE_NOTES", value);
  return import("./gate-note");
}

describe("GateNote", () => {
  it("기본(off)에서는 아무것도 렌더하지 않는다", async () => {
    const { GateNote, SHOW_GATE_NOTES } = await loadGateNote(undefined);
    expect(SHOW_GATE_NOTES).toBe(false);
    const { container } = render(<GateNote>내부 주석</GateNote>);
    expect(container).toBeEmptyDOMElement();
  });

  it("NEXT_PUBLIC_SHOW_GATE_NOTES=1 이면 children을 렌더한다(기본 span)", async () => {
    const { GateNote, SHOW_GATE_NOTES } = await loadGateNote("1");
    expect(SHOW_GATE_NOTES).toBe(true);
    const { container, getByText } = render(<GateNote className="italic">내부 주석</GateNote>);
    expect(getByText("내부 주석")).toBeInTheDocument();
    expect(container.querySelector("span.italic")).not.toBeNull();
  });

  it("as='p' 이면 블록 p로 렌더한다(on)", async () => {
    const { GateNote } = await loadGateNote("true");
    const { container } = render(<GateNote as="p">블록 주석</GateNote>);
    expect(container.querySelector("p")).not.toBeNull();
  });

  it("off일 때 as='p' 여도 렌더하지 않는다", async () => {
    const { GateNote } = await loadGateNote(undefined);
    const { container } = render(<GateNote as="p">블록 주석</GateNote>);
    expect(container).toBeEmptyDOMElement();
  });
});
