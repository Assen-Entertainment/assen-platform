import * as React from "react";
import { cn } from "@/lib/utils";

/** Card — Figma DS Card(16:3). surface + outline + radius.lg, border-first elevation. */
export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("rounded-lg border border-outline bg-surface", className)}
      {...props}
    />
  ),
);
Card.displayName = "Card";

export const CardBody = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-2 p-4", className)} {...props} />
  ),
);
CardBody.displayName = "CardBody";
