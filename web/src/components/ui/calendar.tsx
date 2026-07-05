"use client";
import * as React from "react";
import { cn } from "@/lib/utils";
import { ChevronLeftIcon, ChevronRightIcon } from "@/lib/icons";

/**
 * Calendar — DS 자체 구현 월 그리드(Radix 미제공). 단일 날짜 선택(range 스코프 밖).
 * a11y: role="grid" + columnheader + gridcell(aria-selected/aria-disabled), 화살표 내비(roving tabindex),
 * Enter/Space 선택, PageUp/Down 월 이동. 한국어 로케일(요일 일~토, "YYYY년 M월"). min/max 범위 밖은 aria-disabled.
 */

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"] as const;
const WEEKDAY_FULL = ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"] as const;

/** 시간 무시 날짜 키(YYYYMMDD 정수) — 범위/동일 비교용. */
function dayKey(d: Date): number {
  return d.getFullYear() * 10000 + d.getMonth() * 100 + d.getDate();
}
function isSameDay(a: Date | null | undefined, b: Date | null | undefined): boolean {
  return !!a && !!b && dayKey(a) === dayKey(b);
}
function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}
function addDays(d: Date, n: number): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
}
/**
 * n개월 이동 — day-of-month 보존, 대상 월에 그 날이 없으면 말일로 클램프(APG 관례).
 * 예: 7/31 +1월 → 8/31, 1/31 +1월 → 2/28(비윤년)·2/29(윤년).
 * `new Date(y, m+1, 0)` = 대상 월(m)의 말일 → daysInMonth 재사용(그리드 계산과 동일 공식).
 */
function addMonths(d: Date, n: number): Date {
  const y = d.getFullYear();
  const m = d.getMonth() + n;
  const lastDay = new Date(y, m + 1, 0).getDate();
  return new Date(y, m, Math.min(d.getDate(), lastDay));
}
/** 날짜를 [min, max] 범위(경계 포함)로 클램프 — PageUp/Down이 범위 밖으로 포커스를 넘기지 않게. */
function clampToRange(d: Date, min?: Date, max?: Date): Date {
  if (min && dayKey(d) < dayKey(min)) return new Date(min.getFullYear(), min.getMonth(), min.getDate());
  if (max && dayKey(d) > dayKey(max)) return new Date(max.getFullYear(), max.getMonth(), max.getDate());
  return d;
}
/** 한국어 전체 날짜 라벨(스크린리더용). */
function fullLabel(d: Date): string {
  return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일 ${WEEKDAY_FULL[d.getDay()]}`;
}

export interface CalendarProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "onSelect"> {
  /** 선택 값(controlled). */
  value?: Date | null;
  /** 날짜 선택 콜백. */
  onSelect?: (date: Date) => void;
  /** 선택 가능한 최소/최대 날짜(경계 포함). */
  min?: Date;
  max?: Date;
  /** 초기 표시 월(미지정 시 value 또는 오늘). */
  defaultMonth?: Date;
  /** 마운트 시 포커스 날짜에 focus (팝오버 오픈 시 사용). */
  autoFocus?: boolean;
  /** 그리드 aria-label. */
  ["aria-label"]?: string;
}

export const Calendar = React.forwardRef<HTMLDivElement, CalendarProps>(
  ({ value, onSelect, min, max, defaultMonth, autoFocus, className, "aria-label": ariaLabel, ...props }, ref) => {
    const today = React.useMemo(() => new Date(), []);
    const initial = value ?? defaultMonth ?? today;
    const [viewMonth, setViewMonth] = React.useState<Date>(() => startOfMonth(initial));
    // 포커스 대상 날짜(roving tabindex). 선택값이 현재 월에 있으면 그것, 아니면 오늘 또는 1일.
    const [focused, setFocused] = React.useState<Date>(() => initial);
    const gridRef = React.useRef<HTMLDivElement>(null);
    const didAutoFocus = React.useRef(false);

    const minKey = min ? dayKey(min) : -Infinity;
    const maxKey = max ? dayKey(max) : Infinity;
    const isDisabled = React.useCallback(
      (d: Date) => dayKey(d) < minKey || dayKey(d) > maxKey,
      [minKey, maxKey],
    );

    // 표시 월이 바뀌면 포커스 날짜를 그 월 안으로 당긴다(경계 밖이면 1일).
    React.useEffect(() => {
      setFocused((f) =>
        f.getFullYear() === viewMonth.getFullYear() && f.getMonth() === viewMonth.getMonth()
          ? f
          : viewMonth,
      );
    }, [viewMonth]);

    // 포커스 날짜 이동 시 해당 버튼으로 실제 DOM 포커스(사용자 상호작용 후에만).
    const focusMovedByKeyboard = React.useRef(false);
    React.useEffect(() => {
      if (!focusMovedByKeyboard.current && !(autoFocus && !didAutoFocus.current)) return;
      const el = gridRef.current?.querySelector<HTMLButtonElement>('[data-focused="true"]');
      el?.focus();
      focusMovedByKeyboard.current = false;
      if (autoFocus) didAutoFocus.current = true;
    });

    const moveFocus = (next: Date) => {
      focusMovedByKeyboard.current = true;
      if (next.getMonth() !== focused.getMonth() || next.getFullYear() !== focused.getFullYear()) {
        setViewMonth(startOfMonth(next));
      }
      setFocused(next);
    };

    const select = (d: Date) => {
      if (isDisabled(d)) return;
      onSelect?.(d);
    };

    const onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
      switch (e.key) {
        case "ArrowLeft":
          e.preventDefault();
          moveFocus(addDays(focused, -1));
          break;
        case "ArrowRight":
          e.preventDefault();
          moveFocus(addDays(focused, 1));
          break;
        case "ArrowUp":
          e.preventDefault();
          moveFocus(addDays(focused, -7));
          break;
        case "ArrowDown":
          e.preventDefault();
          moveFocus(addDays(focused, 7));
          break;
        case "Home":
          e.preventDefault();
          moveFocus(addDays(focused, -focused.getDay()));
          break;
        case "End":
          e.preventDefault();
          moveFocus(addDays(focused, 6 - focused.getDay()));
          break;
        case "PageUp":
          e.preventDefault();
          // day-of-month 보존(말일 클램프) 후 [min,max] 클램프. moveFocus가 viewMonth 동기화·DOM 포커스 처리.
          moveFocus(clampToRange(addMonths(focused, -1), min, max));
          break;
        case "PageDown":
          e.preventDefault();
          moveFocus(clampToRange(addMonths(focused, 1), min, max));
          break;
        case "Enter":
        case " ":
          e.preventDefault();
          select(focused);
          break;
        default:
      }
    };

    // 월 그리드(선행 공백 + 1..말일). 6주(42칸)로 고정해 레이아웃 시프트 방지.
    const firstWeekday = viewMonth.getDay();
    const daysInMonth = new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1, 0).getDate();
    const cells: (Date | null)[] = [];
    for (let i = 0; i < firstWeekday; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(viewMonth.getFullYear(), viewMonth.getMonth(), d));
    while (cells.length % 7 !== 0) cells.push(null);
    const weeks: (Date | null)[][] = [];
    for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));

    const monthLabel = `${viewMonth.getFullYear()}년 ${viewMonth.getMonth() + 1}월`;

    return (
      <div ref={ref} className={cn("w-72 select-none p-3", className)} {...props}>
        <div className="mb-2 flex items-center justify-between">
          <button
            type="button"
            aria-label="이전 달"
            onClick={() => setViewMonth((m) => addMonths(m, -1))}
            className="flex size-8 items-center justify-center rounded-md text-on-surface-variant transition-colors hover:bg-surface-container-high [&>svg]:size-5"
          >
            <ChevronLeftIcon />
          </button>
          <span aria-live="polite" className="text-title-m text-on-surface">
            {monthLabel}
          </span>
          <button
            type="button"
            aria-label="다음 달"
            onClick={() => setViewMonth((m) => addMonths(m, 1))}
            className="flex size-8 items-center justify-center rounded-md text-on-surface-variant transition-colors hover:bg-surface-container-high [&>svg]:size-5"
          >
            <ChevronRightIcon />
          </button>
        </div>

        <div
          ref={gridRef}
          role="grid"
          aria-label={ariaLabel ?? monthLabel}
          onKeyDown={onKeyDown}
          className="grid grid-cols-7 gap-0.5"
        >
          <div role="row" className="contents">
            {WEEKDAYS.map((w, i) => (
              <span
                key={w}
                role="columnheader"
                aria-label={WEEKDAY_FULL[i]}
                className="flex h-8 items-center justify-center text-caption text-on-surface-variant"
              >
                {w}
              </span>
            ))}
          </div>
          {weeks.map((week, wi) => (
            <div role="row" className="contents" key={wi}>
              {week.map((day, di) => {
                if (!day) return <span role="gridcell" aria-hidden key={di} className="h-9" />;
                const selected = isSameDay(day, value);
                const isFocused = isSameDay(day, focused);
                const disabled = isDisabled(day);
                const isToday = isSameDay(day, today);
                return (
                  <button
                    type="button"
                    role="gridcell"
                    key={di}
                    data-focused={isFocused || undefined}
                    aria-selected={selected}
                    aria-disabled={disabled || undefined}
                    aria-label={fullLabel(day)}
                    aria-current={isToday ? "date" : undefined}
                    tabIndex={isFocused ? 0 : -1}
                    onClick={() => (disabled ? undefined : select(day))}
                    className={cn(
                      "flex h-9 items-center justify-center rounded-md text-body-m tabular-nums transition-colors",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 focus-visible:ring-offset-surface",
                      selected
                        ? "bg-primary text-on-primary hover:bg-primary-hover"
                        : "text-on-surface hover:bg-surface-container-high",
                      !selected && isToday && "font-bold text-primary",
                      disabled && "pointer-events-none opacity-[0.38]",
                    )}
                  >
                    {day.getDate()}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    );
  },
);
Calendar.displayName = "Calendar";
