import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * BottomCTA — Figma DS(86:11). 모바일(<lg) 하단 고정 액션 바(상세/체크아웃 CTA).
 * 기본 lg:hidden(모바일 전용). safe-area 하단 패딩 반영.
 */
export interface BottomCTAProps extends React.HTMLAttributes<HTMLDivElement> {
  /** lg+ 에서도 노출(기본 false=모바일 전용). */
  persistent?: boolean;
}

export const BottomCTA = React.forwardRef<HTMLDivElement, BottomCTAProps>(
  ({ className, persistent, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        // (main) 셸 BottomNav(h-16, z-40)와 같은 bottom-0면 가려짐 → 그 높이(4rem)만큼 띄운다.
        // lg+ 에선 BottomNav가 숨겨지므로 bottom-0으로 원위치(persistent 변형 대비).
        "fixed inset-x-0 bottom-16 z-40 flex items-center gap-3 border-t border-outline bg-surface px-4 py-3 shadow-4 lg:bottom-0",
        "pb-[calc(0.75rem+env(safe-area-inset-bottom))]",
        persistent ? "" : "lg:hidden",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  ),
);
BottomCTA.displayName = "BottomCTA";
