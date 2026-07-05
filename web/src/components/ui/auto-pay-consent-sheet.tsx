"use client";
import * as React from "react";
import { cn } from "@/lib/utils";
import { Checkbox } from "./checkbox";
import { Sheet, SheetContent, SheetTitle, SheetTrigger, SheetClose } from "./sheet";
import { Button } from "./button";
import { GateNote } from "./gate-note";

/**
 * AutoPayConsentSheet — Figma DS(47:9). 정기결제(자동결제) 동의 요약행 + 상세 시트.
 * 요약행: 체크박스 + "정기결제 동의" (+선택 요약) + [자세히] → 시트에 약관 요약.
 * ※ 문구는 법무 게이트 placeholder(단독 확정 금지).
 */
export interface AutoPayConsentSheetProps {
  checked: boolean;
  onCheckedChange: (v: boolean) => void;
  /** 다음 결제일·금액 등 요약(옵션). */
  summary?: string;
  className?: string;
}

export function AutoPayConsentSheet({ checked, onCheckedChange, summary, className }: AutoPayConsentSheetProps) {
  return (
    <div className={cn("flex items-center gap-2 rounded-lg border border-outline bg-surface-container p-3", className)}>
      <Checkbox
        id="autopay-consent"
        checked={checked}
        onCheckedChange={(v) => onCheckedChange(v === true)}
      />
      <label htmlFor="autopay-consent" className="flex-1 text-body-s text-on-surface">
        정기결제(자동결제)에 동의합니다
        {summary ? <span className="block text-caption text-on-surface-variant">{summary}</span> : null}
      </label>
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="ghost" size="sm" type="button">
            자세히
          </Button>
        </SheetTrigger>
        <SheetContent side="bottom" aria-describedby={undefined}>
          <SheetTitle>정기결제 동의 안내</SheetTitle>
          <div className="flex flex-col gap-2 text-body-s text-on-surface-variant">
            <p>멤버십은 매 결제주기마다 등록된 결제수단으로 자동 결제됩니다.</p>
            <p>다음 결제일 전까지 마이페이지 &gt; 구독 관리에서 언제든 해지할 수 있으며, 해지 시 다음 주기부터 결제가 중단됩니다.</p>
            <p>이미 결제된 주기의 이용료는 원칙적으로 환불되지 않습니다.</p>
            <GateNote as="p" className="italic">※ 문구 placeholder — 실제 약관은 법무 검토 후 확정됩니다.</GateNote>
          </div>
          <SheetClose asChild>
            <Button className="mt-2 w-full" type="button">
              확인
            </Button>
          </SheetClose>
        </SheetContent>
      </Sheet>
    </div>
  );
}
