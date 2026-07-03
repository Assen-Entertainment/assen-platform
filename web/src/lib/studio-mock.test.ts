import { describe, it, expect } from "vitest";
import { validateComposerDraft, type ComposerDraft } from "@/lib/studio-mock";

const base: ComposerDraft = { title: "", body: "", visibility: "public", adult: false };

describe("validateComposerDraft", () => {
  it("flags empty title and body", () => {
    const r = validateComposerDraft(base);
    expect(r.valid).toBe(false);
    expect(r.errors.title).toBeTruthy();
    expect(r.errors.body).toBeTruthy();
  });

  it("treats whitespace-only fields as empty", () => {
    const r = validateComposerDraft({ ...base, title: "   ", body: "\n\t " });
    expect(r.valid).toBe(false);
    expect(r.errors.title).toBeTruthy();
    expect(r.errors.body).toBeTruthy();
  });

  it("rejects titles longer than 60 chars", () => {
    const r = validateComposerDraft({ ...base, title: "가".repeat(61), body: "본문" });
    expect(r.valid).toBe(false);
    expect(r.errors.title).toBeTruthy();
    expect(r.errors.body).toBeUndefined();
  });

  it("passes with a valid title and body", () => {
    const r = validateComposerDraft({ ...base, title: "신작 공개", body: "오늘의 일러스트입니다." });
    expect(r.valid).toBe(true);
    expect(r.errors).toEqual({});
  });
});
