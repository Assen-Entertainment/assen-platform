import * as React from "react";
import { cn } from "@/lib/utils";

/** Chip — Figma DS Chip(11:6). 필터/선택 칩. selected=primary, 미선택=surface-container+outline. */
export interface ChipProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  selected?: boolean;
}

export const Chip = React.forwardRef<HTMLButtonElement, ChipProps>(
  ({ selected, className, type = "button", ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      aria-pressed={selected}
      className={cn(
        "inline-flex h-8 items-center justify-center rounded-full px-3.5 text-label transition-colors disabled:pointer-events-none disabled:opacity-[0.38]",
        selected
          ? "bg-primary text-on-primary"
          : "border border-outline bg-surface-container text-on-surface-variant hover:bg-surface-container-high",
        className,
      )}
      {...props}
    />
  ),
);
Chip.displayName = "Chip";
