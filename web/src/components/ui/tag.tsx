import * as React from "react";
import { cn } from "@/lib/utils";

/** Tag — Figma DS Tag(51:5). 인라인 라벨(카테고리·한정 등). 중립 서피스 + 보조 잉크. */
export const Tag = React.forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
  ({ className, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(
        "inline-flex items-center rounded-ms bg-surface-container-high px-2 py-0.5 text-caption text-on-surface-variant",
        className,
      )}
      {...props}
    />
  ),
);
Tag.displayName = "Tag";
