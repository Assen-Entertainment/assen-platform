"use client";
import * as React from "react";
import * as ToastPrimitive from "@radix-ui/react-toast";
import { cn } from "@/lib/utils";

/** Toast/Snackbar — Figma DS Toast(53:13)/Snackbar(116:21). 우하단 viewport(웹UI_기획). */
export const ToastProvider = ToastPrimitive.Provider;

export const ToastViewport = React.forwardRef<
  React.ElementRef<typeof ToastPrimitive.Viewport>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Viewport>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Viewport
    ref={ref}
    className={cn("fixed bottom-0 right-0 z-[60] flex w-full max-w-sm flex-col gap-2 p-4 outline-none", className)}
    {...props}
  />
));
ToastViewport.displayName = "ToastViewport";

export const Toast = React.forwardRef<
  React.ElementRef<typeof ToastPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Root>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Root
    ref={ref}
    className={cn(
      "flex items-center justify-between gap-3 rounded-md border border-outline bg-surface-container-high p-4 shadow-3",
      // slide-in/swipe-out(R5-W3 #1) — 우측에서 진입, 닫힘/스와이프-끝은 우측으로 이탈. reduced-motion 전역 가드로 축소.
      "data-[state=open]:[animation:toast-in_200ms_ease-out] data-[state=closed]:[animation:toast-out_150ms_ease-in]",
      "data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[swipe=move]:transition-none",
      "data-[swipe=cancel]:translate-x-0 data-[swipe=cancel]:transition-transform",
      "data-[swipe=end]:[animation:toast-out_150ms_ease-in]",
      className,
    )}
    {...props}
  />
));
Toast.displayName = "Toast";

export const ToastTitle = React.forwardRef<
  React.ElementRef<typeof ToastPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Title>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Title ref={ref} className={cn("text-label text-on-surface", className)} {...props} />
));
ToastTitle.displayName = "ToastTitle";

export const ToastDescription = React.forwardRef<
  React.ElementRef<typeof ToastPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Description>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Description ref={ref} className={cn("text-body-s text-on-surface-variant", className)} {...props} />
));
ToastDescription.displayName = "ToastDescription";

export const ToastAction = ToastPrimitive.Action;
export const ToastClose = ToastPrimitive.Close;
