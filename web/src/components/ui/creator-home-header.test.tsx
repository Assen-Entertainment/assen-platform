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

describe("CreatorHomeHeader — 연결 글로우 시그니처(서버 확정 팔로우에만)", () => {
  it("서버 확정(justConnected 논스 증가) 순간에만 글로우+확인 마이크로카피를 띄운다", () => {
    const { container, rerender } = render(
      <CreatorHomeHeader {...base} following={false} justConnected={0} onToggleFollow={vi.fn()} />,
    );
    // 확정 전에는 확인 카피·글로우 없음.
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(container.querySelector("[data-connection-glow]")).toBeNull();

    // 뮤테이션 onSuccess에서 부모가 논스를 올림 + following도 true로(정정). 이 순간에만 발화.
    rerender(
      <CreatorHomeHeader {...base} following={true} justConnected={1} onToggleFollow={vi.fn()} />,
    );
    // 성사 순간 role=status로 낭독되는 리추얼 카피(받침 없는 "…트" → 조사 "와").
    expect(screen.getByRole("status")).toHaveTextContent("이제 별빛 일러스트와 연결됐어요");
    // 크리에이터 액센트 연결 글로우(follow 깊이)가 버튼 뒤로 1회 렌더된다.
    expect(container.querySelector("[data-connection-glow='follow']")).not.toBeNull();
  });

  it("낙관적 following false→true 전환만으로는(논스 무변) 발화하지 않는다 — 실패/차단 롤백 방어", () => {
    // 회귀 가드: onMutate 낙관 갱신으로 following만 true가 되고(justConnected는 그대로) 서버가 403
    // (IdentityVerificationRequired) 등으로 실패해 롤백되는 시나리오. 시그니처는 절대 발화하면 안 된다.
    const { container, rerender } = render(
      <CreatorHomeHeader {...base} following={false} justConnected={0} onToggleFollow={vi.fn()} />,
    );
    rerender(
      <CreatorHomeHeader {...base} following={true} justConnected={0} onToggleFollow={vi.fn()} />,
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(container.querySelector("[data-connection-glow]")).toBeNull();
    // 롤백(true→false)에도 물론 무발화.
    rerender(
      <CreatorHomeHeader {...base} following={false} justConnected={0} onToggleFollow={vi.fn()} />,
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(container.querySelector("[data-connection-glow]")).toBeNull();
  });

  it("초기 팔로잉 상태(하이드레이션·논스 존재)에는 발화하지 않는다", () => {
    // 이미 팔로잉으로 로드되고 논스 기준선이 잡혀도(마운트 시 justConnected=3) 발화 없음.
    const { container } = render(
      <CreatorHomeHeader {...base} following={true} justConnected={3} onToggleFollow={vi.fn()} />,
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(container.querySelector("[data-connection-glow]")).toBeNull();
  });

  it("언팔로우 후 재팔로우(논스 재증가)엔 다시 발화한다", () => {
    const { rerender } = render(
      <CreatorHomeHeader {...base} following={true} justConnected={1} onToggleFollow={vi.fn()} />,
    );
    // 언팔로우(성공) — 논스 무변, 무발화.
    rerender(
      <CreatorHomeHeader {...base} following={false} justConnected={1} onToggleFollow={vi.fn()} />,
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    // 재팔로우(서버 확정) — 논스 증가, 재발화.
    rerender(
      <CreatorHomeHeader {...base} following={true} justConnected={2} onToggleFollow={vi.fn()} />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("연결됐어요");
  });
});
