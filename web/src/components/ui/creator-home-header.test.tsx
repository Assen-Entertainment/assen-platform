import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { CreatorHomeHeader } from "./creator-home-header";

// next/link — jsdom 렌더용 경량 목(followersHref 링크 렌더 대비).
vi.mock("next/link", () => ({
  default: ({ href, children, ...p }: { href: unknown; children: React.ReactNode }) => (
    <a href={typeof href === "string" ? href : "/"} {...p}>
      {children}
    </a>
  ),
}));

const base = {
  name: "별빛 일러스트",
  handle: "stellar",
  initial: "별",
  followers: 100,
};

describe("CreatorHomeHeader — 본인 프로필 팔로우·후원 숨김", () => {
  it("타인 프로필(isOwner=false)에선 팔로우·후원 버튼을 보여준다", () => {
    render(
      <CreatorHomeHeader {...base} onToggleFollow={vi.fn()} onGift={vi.fn()} isOwner={false} />,
    );
    expect(screen.getByRole("button", { name: "팔로우" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /후원/ })).toBeInTheDocument();
  });

  it("본인 프로필(isOwner=true)에선 팔로우·후원 버튼을 숨긴다", () => {
    render(
      <CreatorHomeHeader {...base} onToggleFollow={vi.fn()} onGift={vi.fn()} isOwner />,
    );
    expect(screen.queryByRole("button", { name: "팔로우" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "팔로잉" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /후원/ })).not.toBeInTheDocument();
  });
});

describe("CreatorHomeHeader — 연결 글로우 시그니처(팔로우 성사)", () => {
  it("following false→true 성사 순간에만 조용한 확인 마이크로카피를 띄운다", () => {
    const { rerender } = render(
      <CreatorHomeHeader {...base} following={false} onToggleFollow={vi.fn()} />,
    );
    // 팔로우 전에는 확인 카피 없음.
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    rerender(<CreatorHomeHeader {...base} following={true} onToggleFollow={vi.fn()} />);
    // 성사 순간 role=status로 낭독되는 리추얼 카피(받침 없는 "…트" → 조사 "와").
    expect(screen.getByRole("status")).toHaveTextContent("이제 별빛 일러스트와 연결됐어요");
  });

  it("초기 팔로잉 상태(하이드레이션)에는 마이크로카피를 띄우지 않는다", () => {
    render(<CreatorHomeHeader {...base} following={true} onToggleFollow={vi.fn()} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("following 미정(undefined)→true 전환도 성사로 인식해 카피를 띄운다(mock 초기값 대응)", () => {
    // mock 크리에이터는 following 필드가 없어 undefined로 시작 → 첫 팔로우가 undefined→true.
    const { rerender } = render(
      <CreatorHomeHeader {...base} following={undefined} onToggleFollow={vi.fn()} />,
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    rerender(<CreatorHomeHeader {...base} following={true} onToggleFollow={vi.fn()} />);
    expect(screen.getByRole("status")).toHaveTextContent("연결됐어요");
  });
});
