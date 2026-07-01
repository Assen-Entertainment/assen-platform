import * as React from "react";
import { cn } from "@/lib/utils";
import { SearchIcon } from "@/lib/icons";

/** SearchField — Figma DS(16:8). chrome: surfaceContainerHigh·radius full·검색 아이콘+placeholder(Body/M). A·E. */
export type SearchFieldProps = React.InputHTMLAttributes<HTMLInputElement>;

export const SearchField = React.forwardRef<HTMLInputElement, SearchFieldProps>(
  ({ className, placeholder = "검색", ...props }, ref) => (
    <div
      className={cn(
        "flex h-12 items-center gap-2 rounded-full bg-surface-container-high px-4 focus-within:ring-2 focus-within:ring-primary",
        className,
      )}
    >
      <SearchIcon aria-hidden className="size-5 shrink-0 text-on-surface-variant" />
      <input
        ref={ref}
        type="search"
        placeholder={placeholder}
        className="w-full bg-transparent text-body-m text-on-surface placeholder:text-on-surface-variant focus:outline-none"
        {...props}
      />
    </div>
  ),
);
SearchField.displayName = "SearchField";
