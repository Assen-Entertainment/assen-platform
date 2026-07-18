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
