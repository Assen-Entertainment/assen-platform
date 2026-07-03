import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/lib/utils";

/**
 * TextLink — Figma DS TextLink(51:17). 본문/메타 인라인 링크. primary 잉크 + 밑줄(hover 강조).
 * asChild 로 next/link 등에 합성(Button 패턴 동일). 기본은 <a>.
 */
export interface TextLinkProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  asChild?: boolean;
}

export const TextLink = React.forwardRef<HTMLAnchorElement, TextLinkProps>(
  ({ className, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "a";
    return (
      <Comp
        ref={ref}
        className={cn(
          "text-body-m text-primary underline underline-offset-2 transition-opacity hover:opacity-80",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface rounded-xs",
          className,
        )}
        {...props}
      />
    );
  },
);
TextLink.displayName = "TextLink";
