"use client";
import * as React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { cn } from "@/lib/utils";

/** Tooltip — Figma DS Tooltip(54:10). 반전(on-surface bg / surface text), shadow-2. */
export const TooltipProvider = TooltipPrimitive.Provider;
export const Tooltip = TooltipPrimitive.Root;
export const TooltipTrigger = TooltipPrimitive.Trigger;

export const TooltipContent = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 6, ...props }, ref) => (
  <TooltipPrimitive.Portal>
    <TooltipPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        "z-50 max-w-xs rounded-md bg-on-surface px-2 py-1 text-caption text-surface shadow-2",
        // fade+zoom(R5-W3 #1) — Tooltip open 상태는 delayed-open/instant-open. reduced-motion 전역 가드로 축소.
        "origin-[var(--radix-tooltip-content-transform-origin)] data-[state=delayed-open]:[animation:popover-in_150ms_ease-out] data-[state=instant-open]:[animation:popover-in_150ms_ease-out] data-[state=closed]:[animation:popover-out_120ms_ease-in]",
        className,
      )}
      {...props}
    />
  </TooltipPrimitive.Portal>
));
TooltipContent.displayName = "TooltipContent";
