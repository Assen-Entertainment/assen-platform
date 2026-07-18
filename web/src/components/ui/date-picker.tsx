"use client";
import * as React from "react";
import { cn } from "@/lib/utils";
import { CalendarIcon } from "@/lib/icons";
import { Calendar, type CalendarProps } from "./calendar";

/**
 * DatePicker — TextField 룩의 트리거 + 자체 팝오버(Radix Popover 미도입) + Calendar.
 * 단일 날짜(range 스코프 밖). 클릭 밖/Escape 닫힘, 오픈 시 그리드로 포커스 이동, 닫힘 시 트리거로 복귀.
 * SSR 안전(모듈 스코프 window 접근 없음).
 */
function formatKo(d: Date): string {
  return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일`;
}

export interface DatePickerProps extends Pick<CalendarProps, "min" | "max" | "defaultMonth"> {
  value?: Date | null;
  onChange?: (date: Date) => void;
  /** 미선택 시 표시 텍스트. */
  placeholder?: string;
  /** 접근성 라벨(트리거). */
  ["aria-label"]?: string;
  id?: string;
  disabled?: boolean;
  className?: string;
}

export const DatePicker = React.forwardRef<HTMLButtonElement, DatePickerProps>(
  (
    { value, onChange, min, max, defaultMonth, placeholder = "날짜 선택", disabled, id, className, ...props },
    ref,
  ) => {
    const [open, setOpen] = React.useState(false);
    const wrapRef = React.useRef<HTMLDivElement>(null);
    const triggerRef = React.useRef<HTMLButtonElement>(null);
    React.useImperativeHandle(ref, () => triggerRef.current as HTMLButtonElement);

    // 클릭 밖 → 닫기(트리거 포커스 복귀 없음, 사용자가 다른 곳을 눌렀으므로).
    React.useEffect(() => {
      if (!open) return;
      const onPointerDown = (e: PointerEvent) => {
        if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
      };
      document.addEventListener("pointerdown", onPointerDown);
      return () => document.removeEventListener("pointerdown", onPointerDown);
    }, [open]);

    const close = (returnFocus: boolean) => {
      setOpen(false);
      if (returnFocus) triggerRef.current?.focus();
    };

    const onKeyDown = (e: React.KeyboardEvent) => {
      if (e.key === "Escape" && open) {
        e.preventDefault();
        close(true);
      }
    };

    return (
      <div ref={wrapRef} className={cn("relative inline-block", className)}>
        <button
          ref={triggerRef}
          type="button"
          id={id}
          disabled={disabled}
          aria-haspopup="dialog"
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
          onKeyDown={onKeyDown}
          className={cn(
            "flex h-12 w-full min-w-56 items-center justify-between gap-2 rounded-md border bg-surface px-3 text-body-m",
            "border-outline text-on-surface transition-colors hover:bg-surface-container-high",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface",
            disabled && "pointer-events-none opacity-[0.38]",
          )}
          {...props}
        >
          <span className={cn(!value && "text-on-surface-variant")}>
            {value ? formatKo(value) : placeholder}
          </span>
          <CalendarIcon aria-hidden className="size-5 shrink-0 text-on-surface-variant" />
        </button>

        {open ? (
          // WAI-ARIA APG 팝오버/다이얼로그 표준 패턴(Escape 닫기). role="dialog"는 jsx-a11y가
          // non-interactive로 분류하지만 팝오버 컨테이너의 키보드 핸들링은 의도된 접근성 구현이다.
          // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions
          <div
            role="dialog"
            aria-label="날짜 선택 달력"
            onKeyDown={onKeyDown}
            className={cn(
              "absolute left-0 top-full z-50 mt-2 rounded-lg border border-outline bg-surface shadow-2",
              "data-[state=open]:[animation:popover-in_150ms_ease-out]",
            )}
            data-state="open"
          >
            <Calendar
              autoFocus
              value={value}
              min={min}
              max={max}
              defaultMonth={value ?? defaultMonth}
              onSelect={(d) => {
                onChange?.(d);
                close(true);
              }}
            />
          </div>
        ) : null}
      </div>
    );
  },
);
DatePicker.displayName = "DatePicker";
