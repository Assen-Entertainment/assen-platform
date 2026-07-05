import { describe, it, expect } from "vitest";
import * as React from "react";
import { render, screen } from "@testing-library/react";
import { BottomNav, type BottomNavItem } from "@/components/ui/bottom-nav";

const ITEMS: BottomNavItem[] = [
  { icon: <span>H</span>, label: "홈", href: "/discovery" },
  { icon: <span>M</span>, label: "마이", href: "/mypage" },
];

describe("BottomNav linkComponent 주입", () => {
  it("기본값은 원시 <a>로 렌더한다(DS 이식성)", () => {
    render(<BottomNav items={ITEMS} activeHref="/discovery" />);
    const home = screen.getByRole("link", { name: /홈/ });
    expect(home.tagName).toBe("A");
    expect(home).toHaveAttribute("href", "/discovery");
  });

  it("활성 항목에 aria-current=page를 유지한다", () => {
    render(<BottomNav items={ITEMS} activeHref="/mypage" />);
    expect(screen.getByRole("link", { name: /마이/ })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /홈/ })).not.toHaveAttribute("aria-current");
  });

  it("주입한 linkComponent로 렌더하고 href·aria-current를 전달한다", () => {
    const Injected = ({ href, children, ...rest }: React.ComponentProps<"a">) => (
      <a data-injected="1" href={href} {...rest}>
        {children}
      </a>
    );
    render(<BottomNav items={ITEMS} activeHref="/mypage" linkComponent={Injected} />);
    const my = screen.getByRole("link", { name: /마이/ });
    expect(my).toHaveAttribute("data-injected", "1");
    expect(my).toHaveAttribute("aria-current", "page");
  });
});
