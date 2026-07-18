import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { usePersistentToggle } from "@/lib/use-persistent-state";

function Probe({ storageKey, def }: { storageKey: string; def: boolean }) {
  const [on, setOn] = usePersistentToggle(storageKey, def);
  return (
    <div>
      <span data-testid="state">{on ? "on" : "off"}</span>
      <button onClick={() => setOn(!on)}>toggle</button>
    </div>
  );
}

describe("usePersistentToggle", () => {
  beforeEach(() => localStorage.clear());

  it("persists toggled value to localStorage", async () => {
    const user = userEvent.setup();
    render(<Probe storageKey="assen.test.toggle" def={false} />);
    expect(screen.getByTestId("state").textContent).toBe("off");

    await user.click(screen.getByText("toggle"));
    expect(screen.getByTestId("state").textContent).toBe("on");
    expect(localStorage.getItem("assen.test.toggle")).toBe("1");
  });

  it("restores a persisted value on mount", async () => {
    localStorage.setItem("assen.test.toggle", "1");
    render(<Probe storageKey="assen.test.toggle" def={false} />);
    await waitFor(() => expect(screen.getByTestId("state").textContent).toBe("on"));
  });
});
