import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { Calendar } from "@/components/ui/calendar";
import { DatePicker } from "@/components/ui/date-picker";

// 결정적 기준월(2026년 7월). value 미지정 → 초기 포커스=defaultMonth 1일.
const JULY = new Date(2026, 6, 1);

describe("Calendar (ASS-209)", () => {
  it("aria-grid 구조: grid + 7 columnheader + 요일 라벨", () => {
    render(<Calendar defaultMonth={JULY} aria-label="달력" />);
    const grid = screen.getByRole("grid", { name: "달력" });
    expect(within(grid).getAllByRole("columnheader")).toHaveLength(7);
    expect(within(grid).getByRole("columnheader", { name: "일요일" })).toBeInTheDocument();
  });

  it("월 라벨과 이전/다음 달 이동", () => {
    render(<Calendar defaultMonth={JULY} />);
    expect(screen.getByText("2026년 7월")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "다음 달" }));
    expect(screen.getByText("2026년 8월")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "이전 달" }));
    fireEvent.click(screen.getByRole("button", { name: "이전 달" }));
    expect(screen.getByText("2026년 6월")).toBeInTheDocument();
  });

  it("화살표 키로 포커스가 이동한다(roving tabindex)", () => {
    render(<Calendar defaultMonth={JULY} />);
    const grid = screen.getByRole("grid");
    // 초기 포커스 = 7월 1일(tabIndex 0).
    const day1 = screen.getByRole("gridcell", { name: /2026년 7월 1일/ });
    expect(day1).toHaveAttribute("tabindex", "0");
    fireEvent.keyDown(grid, { key: "ArrowRight" });
    const day2 = screen.getByRole("gridcell", { name: /2026년 7월 2일/ });
    expect(day2).toHaveFocus();
    expect(day2).toHaveAttribute("tabindex", "0");
    fireEvent.keyDown(grid, { key: "ArrowDown" });
    expect(screen.getByRole("gridcell", { name: /2026년 7월 9일/ })).toHaveFocus();
  });

  it("Enter 로 포커스한 날짜를 선택한다", () => {
    const onSelect = vi.fn();
    render(<Calendar defaultMonth={JULY} onSelect={onSelect} />);
    const grid = screen.getByRole("grid");
    fireEvent.keyDown(grid, { key: "ArrowRight" }); // 7월 2일로 이동
    fireEvent.keyDown(grid, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect((onSelect.mock.calls[0][0] as Date).getDate()).toBe(2);
  });

  it("PageDown 은 day-of-month 를 보존한다(7/31 → 8/31, APG 관례)", () => {
    render(<Calendar value={new Date(2026, 6, 31)} defaultMonth={JULY} />);
    const grid = screen.getByRole("grid");
    fireEvent.keyDown(grid, { key: "PageDown" });
    expect(screen.getByText("2026년 8월")).toBeInTheDocument();
    expect(screen.getByRole("gridcell", { name: /2026년 8월 31일/ })).toHaveFocus();
  });

  it("PageDown 은 대상 월에 그 날이 없으면 말일로 클램프한다(1/31 → 2/28 비윤년)", () => {
    render(<Calendar value={new Date(2025, 0, 31)} defaultMonth={new Date(2025, 0, 1)} />);
    const grid = screen.getByRole("grid");
    fireEvent.keyDown(grid, { key: "PageDown" });
    expect(screen.getByText("2025년 2월")).toBeInTheDocument();
    expect(screen.getByRole("gridcell", { name: /2025년 2월 28일/ })).toHaveFocus();
  });

  it("PageDown 말일 클램프는 윤년 2월 29일을 인식한다(1/31 → 2/29)", () => {
    render(<Calendar value={new Date(2024, 0, 31)} defaultMonth={new Date(2024, 0, 1)} />);
    const grid = screen.getByRole("grid");
    fireEvent.keyDown(grid, { key: "PageDown" });
    expect(screen.getByText("2024년 2월")).toBeInTheDocument();
    expect(screen.getByRole("gridcell", { name: /2024년 2월 29일/ })).toHaveFocus();
  });

  it("PageDown 이 max 를 넘으면 max 로 포커스를 클램프한다", () => {
    render(<Calendar value={new Date(2026, 6, 31)} max={new Date(2026, 7, 10)} defaultMonth={JULY} />);
    const grid = screen.getByRole("grid");
    fireEvent.keyDown(grid, { key: "PageDown" }); // 8/31 목표 → max(8/10)로 클램프
    expect(screen.getByText("2026년 8월")).toBeInTheDocument();
    expect(screen.getByRole("gridcell", { name: /2026년 8월 10일/ })).toHaveFocus();
  });

  it("PageUp 이 min 보다 이르면 min 으로 포커스를 클램프한다", () => {
    render(<Calendar value={new Date(2026, 6, 31)} min={new Date(2026, 6, 15)} defaultMonth={JULY} />);
    const grid = screen.getByRole("grid");
    fireEvent.keyDown(grid, { key: "PageUp" }); // 6/30 목표 → min(7/15)로 클램프(여전히 7월)
    expect(screen.getByText("2026년 7월")).toBeInTheDocument();
    expect(screen.getByRole("gridcell", { name: /2026년 7월 15일/ })).toHaveFocus();
  });

  it("min/max 밖 날짜는 aria-disabled 이고 선택되지 않는다", () => {
    const onSelect = vi.fn();
    render(
      <Calendar defaultMonth={JULY} min={new Date(2026, 6, 10)} max={new Date(2026, 6, 20)} onSelect={onSelect} />,
    );
    const outside = screen.getByRole("gridcell", { name: /2026년 7월 5일/ });
    expect(outside).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(outside);
    expect(onSelect).not.toHaveBeenCalled();
    // 범위 안(15일)은 선택 가능.
    fireEvent.click(screen.getByRole("gridcell", { name: /2026년 7월 15일/ }));
    expect(onSelect).toHaveBeenCalledTimes(1);
  });
});

describe("DatePicker (ASS-209)", () => {
  it("미선택 시 placeholder, 클릭 시 달력 다이얼로그가 열린다", () => {
    render(<DatePicker value={null} onChange={() => {}} defaultMonth={JULY} aria-label="날짜" placeholder="날짜 선택" />);
    const trigger = screen.getByRole("button", { name: "날짜" });
    expect(trigger).toHaveTextContent("날짜 선택");
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("dialog", { name: "날짜 선택 달력" })).toBeInTheDocument();
  });

  it("날짜 선택 시 onChange 호출 + 팝오버 닫힘", () => {
    const onChange = vi.fn();
    render(<DatePicker value={null} onChange={onChange} defaultMonth={JULY} aria-label="날짜" />);
    fireEvent.click(screen.getByRole("button", { name: "날짜" }));
    fireEvent.click(screen.getByRole("gridcell", { name: /2026년 7월 15일/ }));
    expect(onChange).toHaveBeenCalledTimes(1);
    expect((onChange.mock.calls[0][0] as Date).getDate()).toBe(15);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("Escape 로 닫힌다", () => {
    render(<DatePicker value={null} onChange={() => {}} defaultMonth={JULY} aria-label="날짜" />);
    fireEvent.click(screen.getByRole("button", { name: "날짜" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
