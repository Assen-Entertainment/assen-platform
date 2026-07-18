"use client";
import * as React from "react";
import { cn } from "@/lib/utils";

/** TextField — Figma DS TextField(10:8) 매핑. label+input+helper/error, 토큰 바인딩, focus ring. */
export interface TextFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: boolean;
  errorText?: string;
}

export const TextField = React.forwardRef<HTMLInputElement, TextFieldProps>(
  ({ className, label, helperText, error, errorText, id, disabled, ...props }, ref) => {
    const autoId = React.useId();
    const inputId = id ?? autoId;
    const msg = error && errorText ? errorText : helperText;
    const descId = msg ? `${inputId}-desc` : undefined;
    return (
      <div className={cn("flex flex-col gap-1.5", disabled && "opacity-[0.38]")}>
        {label ? (
          <label htmlFor={inputId} className="text-label text-on-surface">
            {label}
          </label>
        ) : null}
        <input
          ref={ref}
          id={inputId}
          disabled={disabled}
          aria-invalid={error || undefined}
          aria-describedby={descId}
          className={cn(
            "h-12 w-full rounded-md border bg-surface px-3 text-body-m text-on-surface",
            "placeholder:text-on-surface-variant focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-surface",
            error ? "border-error" : "border-outline",
            className,
          )}
          {...props}
        />
        {msg ? (
          <p id={descId} className={cn("text-caption", error ? "text-error" : "text-on-surface-variant")}>
            {msg}
          </p>
        ) : null}
      </div>
    );
  },
);
TextField.displayName = "TextField";
