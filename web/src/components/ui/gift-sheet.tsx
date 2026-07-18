"use client";
import * as React from "react";
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Chip } from "@/components/ui/chip";
import { TextArea } from "@/components/ui/text-area";
import { Button } from "@/components/ui/button";
import { SuccessCheck } from "@/components/ui/success-check";
import { won } from "@/lib/checkout";

/**
 * GiftSheet — Figma DS(28:21). 저마찰 1회성 후원(루브릭 #25·#41, Buy Me a Coffee/Ko-fi 참조).
 * 금액 프리셋 칩 + 커스텀 입력 + 응원 메시지 → 후원하기 → mock 완료 딜라이트(SuccessCheck).
 * ※ 실 결제/PG 연동은 대표·법무 게이트 — 본 흐름은 UI mock 이다.
 */
const PRESETS = [1000, 3000, 5000, 10000] as const;

export interface GiftSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** 후원 대상 크리에이터 표시명. */
  creatorName: string;
  /** 완료 콜백(mock). 금액·메시지 전달. */
  onComplete?: (amount: number, message: string) => void;
}

export function GiftSheet({ open, onOpenChange, creatorName, onComplete }: GiftSheetProps) {
  const [preset, setPreset] = React.useState<number | null>(3000);
  const [custom, setCustom] = React.useState("");
  const [message, setMessage] = React.useState("");
  const [done, setDone] = React.useState(false);

  const customAmount = Number(custom.replace(/[^0-9]/g, ""));
  const amount = custom ? customAmount : (preset ?? 0);
  const canGift = amount > 0 && !done;

  // 시트가 닫히면 상태 초기화(다음 오픈 때 깨끗한 시작).
  React.useEffect(() => {
    if (!open) {
      const t = setTimeout(() => {
        setDone(false);
        setPreset(3000);
        setCustom("");
        setMessage("");
      }, 200);
      return () => clearTimeout(t);
    }
  }, [open]);

  const gift = () => {
    if (!canGift) return;
    setDone(true);
    onComplete?.(amount, message.trim());
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="sm:mx-auto sm:max-w-md">
        {done ? (
          <div className="flex flex-col items-center gap-3 py-4 text-center">
            <SuccessCheck label="후원 완료" />
            <SheetTitle className="text-title-l text-on-surface">후원해 주셔서 고마워요!</SheetTitle>
            <SheetDescription className="text-body-m text-on-surface-variant">
              {creatorName}님에게 {won(amount)}을 전달했어요.
            </SheetDescription>
            <Button className="mt-1 w-full" onClick={() => onOpenChange(false)}>
              닫기
            </Button>
            <p className="text-caption text-on-surface-variant">※ 데모 — 실제 결제 미연동(게이트)</p>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <SheetTitle className="text-title-l text-on-surface">{creatorName}님 후원하기</SheetTitle>
              <SheetDescription className="text-body-s text-on-surface-variant">
                응원의 마음을 금액으로 전해보세요. 로그인 없이 간편하게.
              </SheetDescription>
            </div>

            <div className="flex flex-wrap gap-2">
              {PRESETS.map((v) => (
                <Chip
                  key={v}
                  selected={!custom && preset === v}
                  onClick={() => {
                    setPreset(v);
                    setCustom("");
                  }}
                >
                  {won(v)}
                </Chip>
              ))}
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="gift-custom" className="text-label text-on-surface">
                직접 입력
              </label>
              <div className="flex items-center gap-2 rounded-md border border-outline bg-surface px-3 py-2.5 focus-within:ring-2 focus-within:ring-primary focus-within:ring-offset-2 focus-within:ring-offset-surface">
                <span className="text-body-m text-on-surface-variant">₩</span>
                <input
                  id="gift-custom"
                  inputMode="numeric"
                  value={custom}
                  onChange={(e) => setCustom(e.target.value)}
                  placeholder="원하는 금액"
                  className="w-full bg-transparent text-body-m tabular-nums text-on-surface outline-none placeholder:text-on-surface-variant"
                />
              </div>
            </div>

            <TextArea
              label="응원 메시지 (선택)"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="크리에이터에게 남길 한마디"
              maxLength={100}
              showCount
              className="min-h-20"
            />

            <Button size="lg" className="w-full" disabled={!canGift} onClick={gift}>
              {amount > 0 ? `${won(amount)} 후원하기` : "금액을 선택하세요"}
            </Button>
            <p className="text-center text-caption text-on-surface-variant">
              ※ 실결제/PG 연동은 대표·법무 게이트 — 본 흐름은 UI mock입니다.
            </p>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
