import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionProvider, useSession } from "@/lib/session";

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
