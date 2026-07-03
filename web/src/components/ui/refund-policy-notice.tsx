import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * RefundPolicyNotice — Figma DS(45:16). 환불·청약철회 안내 + 신뢰 시그널.
 * ※ 문구는 placeholder(가격·약관은 대표·법무 게이트). 실제 약관 확정 전 임시 표기.
 */
export interface RefundPolicyNoticeProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 통신판매중개 면책 등 신뢰 시그널 행 표시(기본 true). */
  showTrust?: boolean;
}

const REFUND_POINTS = [
  "디지털/다운로드 상품은 열람·다운로드 시작 후 청약철회가 제한될 수 있습니다.",
  "실물 상품은 수령 후 7일 이내 단순변심 환불이 가능합니다(왕복 배송비 부담).",
  "환불은 결제수단 원복 기준 영업일 3~5일 내 처리됩니다.",
];

export function RefundPolicyNotice({ showTrust = true, className, ...props }: RefundPolicyNoticeProps) {
  return (
    <div
      className={cn("flex flex-col gap-2 rounded-lg border border-outline bg-surface-container p-4", className)}
      {...props}
    >
      <p className="text-label text-on-surface">환불·청약철회 안내</p>
      <ul className="flex list-disc flex-col gap-1 pl-4 text-body-s text-on-surface-variant">
        {REFUND_POINTS.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>
      {showTrust ? (
        <p className="mt-1 border-t border-outline pt-2 text-caption text-on-surface-variant">
          안전결제(에스크로) 적용 · Assen은 통신판매중개자로서 거래 당사자가 아니며 상품·거래 책임은 판매자에게 있습니다.{" "}
          <span className="italic">(문구 placeholder — 법무 확정 전)</span>
        </p>
      ) : null}
    </div>
  );
}
