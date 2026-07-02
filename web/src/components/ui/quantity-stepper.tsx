import { cn } from "@/lib/utils";
import { AddIcon, RemoveIcon } from "@/lib/icons";

/** QuantityStepper — Figma DS(61:9). − [n] + 제어형(value/onChange), min/max 클램프. */
export interface QuantityStepperProps {
  value: number;
  min?: number;
  max?: number;
  onChange?: (value: number) => void;
  className?: string;
}

export function QuantityStepper({ value, min = 1, max = 99, onChange, className }: QuantityStepperProps) {
  const set = (v: number) => onChange?.(Math.max(min, Math.min(max, v)));
  const btn = "flex size-9 items-center justify-center text-on-surface transition-colors hover:bg-surface-container-high disabled:pointer-events-none disabled:opacity-[0.38]";
  return (
    <div className={cn("inline-flex items-center overflow-hidden rounded-md border border-outline", className)}>
      <button type="button" aria-label="수량 감소" disabled={value <= min} onClick={() => set(value - 1)} className={btn}>
        <RemoveIcon className="size-4" />
      </button>
      <span className="min-w-8 text-center text-body-m tabular-nums text-on-surface" aria-live="polite">{value}</span>
      <button type="button" aria-label="수량 증가" disabled={value >= max} onClick={() => set(value + 1)} className={btn}>
        <AddIcon className="size-4" />
      </button>
    </div>
  );
}
