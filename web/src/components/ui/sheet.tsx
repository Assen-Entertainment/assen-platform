"use client";
import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/** Sheet — Figma DS ActionSheet(84:19)/시트류. Radix Dialog 기반. 모바일 bottom / 웹 side(웹UI_기획 매핑). */
export const Sheet = DialogPrimitive.Root;
export const SheetTrigger = DialogPrimitive.Trigger;
export const SheetClose = DialogPrimitive.Close;
export const SheetTitle = DialogPrimitive.Title; // a11y: Radix Dialog는 Title 필수
export const SheetDescription = DialogPrimitive.Description;

const sheetVariants = cva("fixed z-50 flex flex-col gap-3 border-outline bg-surface p-5 shadow-4 focus:outline-none", {
  variants: {
    side: {
      // 방향별 slide-in/out(R5-W3 #1) — enter 200ms ease-out / exit 150ms ease-in. reduced-motion 전역 가드로 축소.
      bottom:
        "inset-x-0 bottom-0 rounded-t-xl border-t data-[state=open]:[animation:sheet-in-bottom_200ms_ease-out] data-[state=closed]:[animation:sheet-out-bottom_150ms_ease-in]",
      right:
        "inset-y-0 right-0 h-full w-[min(90vw,400px)] border-l data-[state=open]:[animation:sheet-in-right_200ms_ease-out] data-[state=closed]:[animation:sheet-out-right_150ms_ease-in]",
      left:
        "inset-y-0 left-0 h-full w-[min(90vw,400px)] border-r data-[state=open]:[animation:sheet-in-left_200ms_ease-out] data-[state=closed]:[animation:sheet-out-left_150ms_ease-in]",
    },
  },
  defaultVariants: { side: "bottom" },
});

export interface SheetContentProps
  extends React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>,
    VariantProps<typeof sheetVariants> {}

export const SheetContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  SheetContentProps
>(({ className, side = "bottom", children, ...props }, ref) => (
  <DialogPrimitive.Portal>
    <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/50 data-[state=open]:[animation:overlay-in_200ms_ease-out] data-[state=closed]:[animation:overlay-out_150ms_ease-in]" />
    <DialogPrimitive.Content ref={ref} className={cn(sheetVariants({ side }), className)} {...props}>
      {side === "bottom" ? <div className="mx-auto mb-1 h-1 w-9 rounded-full bg-outline" /> : null}
      {children}
    </DialogPrimitive.Content>
  </DialogPrimitive.Portal>
));
SheetContent.displayName = "SheetContent";
