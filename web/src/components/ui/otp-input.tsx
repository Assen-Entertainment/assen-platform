"use client";
import * as React from "react";
import { cn } from "@/lib/utils";

/** OTPInput — 본인인증/2FA 코드 입력. 자리별 박스 + 자동 포커스 이동. 제어형. */
export interface OTPInputProps {
  length?: number;
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export function OTPInput({ length = 6, value, onChange, className }: OTPInputProps) {
  const refs = React.useRef<(HTMLInputElement | null)[]>([]);
  const set = (i: number, ch: string) => {
    const d = ch.replace(/\D/g, "").slice(-1);
    const arr = value.split("");
    arr[i] = d;
    onChange(arr.join("").slice(0, length));
    if (d && i < length - 1) refs.current[i + 1]?.focus();
  };
  const onKey = (i: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !value[i] && i > 0) refs.current[i - 1]?.focus();
  };
  return (
    <div className={cn("flex gap-2", className)} role="group" aria-label="인증 코드">
      {Array.from({ length }).map((_, i) => (
        <input
          key={i}
          ref={(el) => {
            refs.current[i] = el;
          }}
          inputMode="numeric"
          maxLength={1}
          aria-label={`자리 ${i + 1}`}
          value={value[i] ?? ""}
          onChange={(e) => set(i, e.target.value)}
          onKeyDown={(e) => onKey(i, e)}
          className="size-12 rounded-md border border-outline bg-surface text-center text-title-m text-on-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        />
      ))}
    </div>
  );
}
