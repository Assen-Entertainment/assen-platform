"use client";
import * as React from "react";
import { cn } from "@/lib/utils";

/** TextArea — Figma DS TextArea(54:7). label+textarea+helper/error, 토큰 바인딩, focus ring. TextField의 멀티라인 짝. */
export interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  helperText?: string;
  error?: boolean;
  errorText?: string;
  /** 우측 하단 글자 수 카운터 노출(현재 길이/maxLength). */
  showCount?: boolean;
}

export const TextArea = React.forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ className, label, helperText, error, errorText, id, disabled, showCount, maxLength, value, ...props }, ref) => {
    const autoId = React.useId();
    const inputId = id ?? autoId;
    const msg = error && errorText ? errorText : helperText;
    const descId = msg ? `${inputId}-desc` : undefined;
    const len = typeof value === "string" ? value.length : 0;
    return (
      <div className={cn("flex flex-col gap-1.5", disabled && "opacity-[0.38]")}>
        {label ? (
          <label htmlFor={inputId} className="text-label text-on-surface">
            {label}
          </label>
        ) : null}
        <textarea
          ref={ref}
          id={inputId}
          disabled={disabled}
          maxLength={maxLength}
          value={value}
          aria-invalid={error || undefined}
          aria-describedby={descId}
          className={cn(
            "min-h-28 w-full resize-y rounded-md border bg-surface px-3 py-2.5 text-body-m text-on-surface",
            "placeholder:text-on-surface-variant focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface",
            error ? "border-error" : "border-outline",
            className,
          )}
          {...props}
        />
        <div className="flex items-center justify-between gap-2">
          {msg ? (
            <p id={descId} className={cn("text-caption", error ? "text-error" : "text-on-surface-variant")}>
              {msg}
            </p>
          ) : (
            <span />
          )}
          {showCount && maxLength ? (
            <span className="shrink-0 text-caption tabular-nums text-on-surface-variant">
              {len}/{maxLength}
            </span>
          ) : null}
        </div>
      </div>
    );
  },
);
TextArea.displayName = "TextArea";
