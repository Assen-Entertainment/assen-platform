import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SiteFooter } from "./site-footer";

describe("SiteFooter", () => {
  it("shows the §10 business info with a pending 통신판매업 신고", () => {
    render(<SiteFooter />);
    // 사업자등록번호(사실 정보) + 신고번호 미발급 → "준비 중"으로 표기.
    expect(screen.getByText(/432-87-03563/)).toBeTruthy();
    expect(screen.getByText(/통신판매업 신고 준비 중/)).toBeTruthy();
  });

  it("discloses the §20 통신판매중개자 (intermediary) status", () => {
    render(<SiteFooter />);
    expect(screen.getByText(/통신판매중개자/)).toBeTruthy();
  });

  it("links to the policy pages", () => {
    render(<SiteFooter />);
    expect(screen.getByRole("link", { name: "이용약관" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "개인정보처리방침" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "환불정책" })).toBeTruthy();
  });
});
