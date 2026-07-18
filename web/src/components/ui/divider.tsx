import * as React from "react";
import { cn } from "@/lib/utils";

/** Divider — Figma DS Divider(12:9). outline 1px (border-first elevation). */
export interface DividerProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: "horizontal" | "vertical";
}

export const Divider = React.forwardRef<HTMLDivElement, DividerProps>(
  ({ className, orientation = "horizontal", ...props }, ref) => (
    <div
      ref={ref}
      role="separator"
      aria-orientation={orientation}
      className={cn(
        orientation === "horizontal" ? "h-px w-full" : "h-full w-px",
        "bg-outline",
        className,
      )}
      {...props}
    />
  ),
);
Divider.displayName = "Divider";
