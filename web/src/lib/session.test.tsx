import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionProvider, useSession, mapMe, coerceKycStatus } from "@/lib/session";

function Probe() {
  const { user, login, logout } = useSession();
  return (
    <div>
      <span data-testid="user">{user ? user.name : "none"}</span>
      <button onClick={() => login({ name: "테스트", handle: "t" })}>login</button>
      <button onClick={() => logout()}>logout</button>
    </div>
  );
}

describe("SessionProvider (mock)", () => {
  beforeEach(() => localStorage.clear());

  it("login stores a mock user and persists to localStorage", async () => {
    const user = userEvent.setup();
    render(
      <SessionProvider>
        <Probe />
      </SessionProvider>,
    );
    expect(screen.getByTestId("user").textContent).toBe("none");
    await user.click(screen.getByText("login"));
    expect(screen.getByTestId("user").textContent).toBe("테스트");
    expect(localStorage.getItem("assen.session")).toContain("테스트");

    await user.click(screen.getByText("logout"));
    expect(screen.getByTestId("user").textContent).toBe("none");
    expect(localStorage.getItem("assen.session")).toBeNull();
  });

  it("restores a persisted session on mount", async () => {
    localStorage.setItem("assen.session", JSON.stringify({ name: "복원됨", handle: "r", role: "fan" }));
    render(
      <SessionProvider>
        <Probe />
      </SessionProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("user").textContent).toBe("복원됨"));
  });
});

describe("mapMe (KYC 매핑, fail-closed)", () => {
  it("adult_verified/kyc_status를 camelCase로 매핑한다", () => {
    const u = mapMe({ id: "u1", nickname: "테스트", role: "fan", adult_verified: true, kyc_status: "verified" });
    expect(u.name).toBe("테스트");
    expect(u.adultVerified).toBe(true);
    expect(u.kycStatus).toBe("verified");
  });

  it("인증 필드 누락 시 fail-closed(false·unverified)로 기본값을 채운다", () => {
    const u = mapMe({ id: "u1", nickname: "n", role: "fan" });
    expect(u.adultVerified).toBe(false);
    expect(u.kycStatus).toBe("unverified");
  });

  it("coerceKycStatus는 미지의 값을 unverified로 강제한다(허용값은 통과)", () => {
    expect(coerceKycStatus("pending")).toBe("pending");
    expect(coerceKycStatus("failed")).toBe("failed");
    expect(coerceKycStatus("bogus")).toBe("unverified");
    expect(coerceKycStatus(undefined)).toBe("unverified");
    expect(coerceKycStatus(42)).toBe("unverified");
  });
});
