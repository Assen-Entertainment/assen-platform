"use client";
import * as React from "react";
import * as MenuPrimitive from "@radix-ui/react-dropdown-menu";
import { cn } from "@/lib/utils";

/** DropdownMenu — Figma DS Menu(85:14). Radix + 토큰(surface/outline/shadow-2). */
export const DropdownMenu = MenuPrimitive.Root;
export const DropdownMenuTrigger = MenuPrimitive.Trigger;

export const DropdownMenuContent = React.forwardRef<
  React.ElementRef<typeof MenuPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof MenuPrimitive.Content>
>(({ className, sideOffset = 6, ...props }, ref) => (
  <MenuPrimitive.Portal>
    <MenuPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        "z-50 min-w-44 rounded-md border border-outline bg-surface p-1 shadow-2",
        // fade+zoom(R5-W3 #1) — 트리거 방향에서 확대. reduced-motion 전역 가드로 축소.
        "origin-[var(--radix-dropdown-menu-content-transform-origin)] data-[state=open]:[animation:popover-in_150ms_ease-out] data-[state=closed]:[animation:popover-out_120ms_ease-in]",
        className,
      )}
      {...props}
    />
  </MenuPrimitive.Portal>
));
DropdownMenuContent.displayName = "DropdownMenuContent";

export const DropdownMenuItem = React.forwardRef<
  React.ElementRef<typeof MenuPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof MenuPrimitive.Item> & { destructive?: boolean }
>(({ className, destructive, ...props }, ref) => (
  <MenuPrimitive.Item
    ref={ref}
    className={cn(
      "flex cursor-pointer select-none items-center rounded-sm px-3 py-2 text-body-m outline-none transition-colors",
      "data-[highlighted]:bg-surface-container-high data-[disabled]:pointer-events-none data-[disabled]:opacity-[0.38]",
      destructive ? "text-error" : "text-on-surface",
      className,
    )}
    {...props}
  />
));
DropdownMenuItem.displayName = "DropdownMenuItem";

export const DropdownMenuSeparator = React.forwardRef<
  React.ElementRef<typeof MenuPrimitive.Separator>,
  React.ComponentPropsWithoutRef<typeof MenuPrimitive.Separator>
>(({ className, ...props }, ref) => (
  <MenuPrimitive.Separator ref={ref} className={cn("my-1 h-px bg-outline-variant", className)} {...props} />
));
DropdownMenuSeparator.displayName = "DropdownMenuSeparator";
