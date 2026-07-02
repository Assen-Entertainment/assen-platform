"use client";
import * as React from "react";
import { cn } from "@/lib/utils";
import { Checkbox } from "@/components/ui/checkbox";

/** ConsentGroup — 약관 동의 묶음. 전체동의 + 개별. 제어형(value=동의된 id 배열). 필수 항목 표기. */
export interface ConsentItem {
  id: string;
  label: string;
  required?: boolean;
}
export interface ConsentGroupProps {
  items: ConsentItem[];
  value: string[];
  onChange: (ids: string[]) => void;
  className?: string;
}

export function ConsentGroup({ items, value, onChange, className }: ConsentGroupProps) {
  const allOn = items.length > 0 && items.every((it) => value.includes(it.id));
  const toggleAll = () => onChange(allOn ? [] : items.map((it) => it.id));
  const toggle = (id: string) =>
    onChange(value.includes(id) ? value.filter((x) => x !== id) : [...value, id]);
  return (
    <div className={cn("flex flex-col gap-3 rounded-lg border border-outline p-4", className)}>
      <label className="flex items-center gap-2 text-label text-on-surface">
        <Checkbox checked={allOn} onCheckedChange={toggleAll} /> 전체 동의
      </label>
      <div className="h-px bg-outline-variant" />
      {items.map((it) => (
        <label key={it.id} className="flex items-center gap-2 text-body-m text-on-surface">
          <Checkbox checked={value.includes(it.id)} onCheckedChange={() => toggle(it.id)} />
          {it.label}
          {it.required ? <span className="text-caption text-error">(필수)</span> : null}
        </label>
      ))}
    </div>
  );
}
