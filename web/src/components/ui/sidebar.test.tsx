import { describe, it, expect } from "vitest";
import * as React from "react";
import { render, screen } from "@testing-library/react";
import { Sidebar, type SidebarNavItem } from "@/components/ui/sidebar";

const ITEMS: SidebarNavItem[] = [
  { icon: <span>H</span>, label: "홈", href: "/discovery" },
  { icon: <span>F</span>, label: "피드", href: "/feed" },
];

describe("Sidebar linkComponent 주입", () => {
  it("기본값은 원시 <a>로 렌더한다(DS 이식성)", () => {
    render(<Sidebar items={ITEMS} activeHref="/discovery" />);
    const home = screen.getByRole("link", { name: /홈/ });
    expect(home.tagName).toBe("A");
    expect(home).toHaveAttribute("href", "/discovery");
  });

  it("활성 항목에 aria-current=page를 유지한다", () => {
    render(<Sidebar items={ITEMS} activeHref="/feed" />);
    expect(screen.getByRole("link", { name: /피드/ })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /홈/ })).not.toHaveAttribute("aria-current");
  });

  it("주입한 linkComponent로 렌더하고 href·aria-current·className을 전달한다", () => {
    const Injected = ({ href, children, ...rest }: React.ComponentProps<"a">) => (
      <a data-injected="1" href={href} {...rest}>
        {children}
      </a>
    );
    render(<Sidebar items={ITEMS} activeHref="/discovery" linkComponent={Injected} />);
    const home = screen.getByRole("link", { name: /홈/ });
    expect(home).toHaveAttribute("data-injected", "1");
    expect(home).toHaveAttribute("aria-current", "page");
    expect(home.className).toContain("text-primary");
  });
});
