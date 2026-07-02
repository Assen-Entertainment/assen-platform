import { cn } from "@/lib/utils";

/** SegmentedControl — Figma DS(85:20). iOS식 세그먼트(track surfaceContainerHigh, 활성=surface+shadow). 단일선택=radiogroup. */
export interface SegmentOption {
  label: string;
  value: string;
}
export interface SegmentedControlProps {
  options: SegmentOption[];
  value: string;
  onValueChange?: (value: string) => void;
  className?: string;
}

export function SegmentedControl({ options, value, onValueChange, className }: SegmentedControlProps) {
  return (
    <div role="radiogroup" className={cn("inline-flex rounded-full bg-surface-container-high p-1", className)}>
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onValueChange?.(o.value)}
            className={cn(
              "rounded-full px-4 py-1.5 text-label transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
              active ? "bg-surface text-on-surface shadow-1" : "text-on-surface-variant hover:text-on-surface",
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
