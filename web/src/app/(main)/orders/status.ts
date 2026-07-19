import type { OrderStatus, RefundStatus } from "@/lib/api";
import type { StatusChipVariant } from "@/components/ui";

/** 주문 상태 → StatusChip 라벨/변형. /orders 목록과 /orders/[id] 상세 공용. */
export function orderStatusMeta(status: OrderStatus): { label: string; variant: StatusChipVariant } {
  switch (status) {
    case "paid":
      // 결제완료=성공/긍정 상태 → 브랜드 퍼플(info)이 아니라 시맨틱 success(그린)로.
      // 구독 "구독 중"과 같은 계열로 통일해 브랜드색 희석·의미 혼선을 제거한다.
      // 브랜드 퍼플(info)은 이제 "진행 중/정보"(배송중·환불처리중)에만 쓰인다.
      return { label: "결제완료", variant: "success" };
    case "shipping":
      return { label: "배송중", variant: "info" };
    case "completed":
      return { label: "완료", variant: "success" };
    case "cancelled":
      return { label: "취소", variant: "neutral" };
    case "refunding":
      return { label: "환불처리중", variant: "info" };
    case "refunded":
      return { label: "환불완료", variant: "neutral" };
  }
}

/** 환불 상태 → StatusChip 라벨/변형. */
export function refundStatusMeta(status: RefundStatus): { label: string; variant: StatusChipVariant } {
  switch (status) {
    case "requested":
      return { label: "환불 접수", variant: "info" };
    case "approved":
      return { label: "환불 완료", variant: "success" };
    case "rejected":
      return { label: "환불 거절", variant: "danger" };
  }
}
