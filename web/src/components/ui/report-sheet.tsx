"use client";
import * as React from "react";
import { Sheet, SheetContent, SheetTitle, SheetDescription, SheetClose } from "@/components/ui/sheet";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio";
import { TextArea } from "@/components/ui/text-area";
import { Button } from "@/components/ui/button";

/**
 * ReportSheet — Figma DS ReportSheet(42:24). 신고 사유 라디오 + 상세 TextArea + 제출.
 * 제출은 onSubmit 콜백으로 위임(소비자가 토스트·라우팅). 사유 미선택 시 제출 비활성.
 * ※기본 사유 value는 서버 FAN_REPORTABLE_TYPES와 정렬 — /safety/fan-reports로 실 접수된다(feed-view).
 */
export interface ReportReason {
  value: string;
  label: string;
}

export interface ReportSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: { reason: string; detail: string }) => void;
  reasons?: ReportReason[];
  title?: string;
  description?: string;
}

// value는 서버 FAN_REPORTABLE_TYPES(apps/safety/services.py) enum 값 — 서버가 그대로
// 소비하므로 변경 시 서버 enum과 함께 유지한다. label만 자연스러운 한국어.
const DEFAULT_REASONS: ReportReason[] = [
  { value: "unwanted_request", label: "원치 않는 요구·부담" },
  { value: "verbal_abuse", label: "욕설·폭언·비방" },
  { value: "photo_violation", label: "사진·영상 무단 촬영·유포" },
  { value: "stalking_concern", label: "스토킹·과도한 접근" },
  { value: "privacy_portrait_concern", label: "개인정보·초상권 침해" },
  { value: "other", label: "기타" },
];

export function ReportSheet({
  open,
  onOpenChange,
  onSubmit,
  reasons = DEFAULT_REASONS,
  title = "신고하기",
  description = "신고 사유를 선택하면 운영팀이 검토합니다. 허위 신고는 제재될 수 있어요.",
}: ReportSheetProps) {
  const [reason, setReason] = React.useState("");
  const [detail, setDetail] = React.useState("");
  const groupId = React.useId();

  // 시트가 닫힐 때 입력 초기화(재오픈 시 잔상 방지).
  React.useEffect(() => {
    if (!open) {
      setReason("");
      setDetail("");
    }
  }, [open]);

  const submit = () => {
    if (!reason) return;
    onSubmit({ reason, detail });
    onOpenChange(false);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="max-h-[85vh] overflow-y-auto sm:mx-auto sm:max-w-md">
        <SheetTitle>{title}</SheetTitle>
        <SheetDescription>{description}</SheetDescription>
        <RadioGroup value={reason} onValueChange={setReason} className="mt-1 gap-1">
          {reasons.map((r) => {
            const id = `${groupId}-${r.value}`;
            return (
              <label
                key={r.value}
                htmlFor={id}
                className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-2.5 text-body-m text-on-surface transition-colors hover:bg-surface-container-high"
              >
                <RadioGroupItem id={id} value={r.value} />
                {r.label}
              </label>
            );
          })}
        </RadioGroup>
        <TextArea
          label="상세 내용 (선택)"
          placeholder="구체적인 상황을 적어주시면 검토에 도움이 됩니다."
          value={detail}
          onChange={(e) => setDetail(e.target.value)}
          maxLength={500}
          showCount
          className="min-h-24"
        />
        <div className="mt-1 flex gap-2">
          <SheetClose asChild>
            <Button variant="outline" className="flex-1">
              취소
            </Button>
          </SheetClose>
          <Button className="flex-1" disabled={!reason} onClick={submit}>
            신고 제출
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
