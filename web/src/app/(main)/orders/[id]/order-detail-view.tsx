"use client";
import * as React from "react";
import Link from "next/link";
import {
  Card,
  CardBody,
  Divider,
  Button,
  Badge,
  StatusChip,
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { useOrder, useCancelOrder, useRequestRefund } from "@/lib/api/queries";
import { won } from "@/lib/checkout";
import { PRODUCT_TYPE_LABEL } from "@/lib/product-labels";
import { orderStatusMeta, refundStatusMeta } from "../status";
import { ApiError, apiErrorMessage, type Order } from "@/lib/api";

const REFUND_REASONS = ["단순 변심", "상품 불량·파손", "배송 지연", "상품 정보와 다름", "기타"];

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-center justify-between text-body-m">
      <span className="text-on-surface-variant">{label}</span>
      <span className={strong ? "text-title-m tabular-nums text-on-surface" : "tabular-nums text-on-surface"}>
        {value}
      </span>
    </div>
  );
}

export function OrderDetailView({ order }: { order: Order }) {
  const { toast } = useToast();
  // USE_API면 실 조회/취소/환불, 아니면 mock — 낙관적 상태 전환은 캐시로 반영.
  const { data } = useOrder(order.id, order);
  const o = data ?? order;
  const cancelMut = useCancelOrder(order.id);
  const refundMut = useRequestRefund(order.id);
  const [reason, setReason] = React.useState(REFUND_REASONS[0]);

  const status = o.status;
  const refund = o.refund ?? null;
  const s = orderStatusMeta(status);
  const canCancel = status === "paid" || status === "shipping";
  const canRefund = (status === "completed" || status === "shipping") && !refund;

  // 실패 안내 — 서버 error code(OrderNotCancellable·OrderNotRefundable·OpenRefundExists 등)를
  // apiErrorMessage로 한국어 매핑(detail 표시 폴백). 401은 전역 세션 가드가 처리 → 그 외만 토스트.
  const failToast = (title: string, e: unknown) => {
    if (e instanceof ApiError && e.status === 401) return;
    toast({ title, description: apiErrorMessage(e) });
  };

  const doCancel = () => {
    cancelMut.mutate(undefined, {
      onSuccess: () => toast({ title: "주문이 취소됐어요", description: `${o.id} · ${won(o.total)} 환불 예정` }),
      onError: (e) => failToast("주문을 취소하지 못했어요", e),
    });
  };

  const doRefund = () => {
    refundMut.mutate(
      { reason },
      {
        onSuccess: () => toast({ title: "환불 신청이 접수됐어요", description: `사유: ${reason}` }),
        onError: (e) => failToast("환불 신청을 접수하지 못했어요", e),
      },
    );
  };

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Link href="/orders" className="text-body-s text-on-surface-variant hover:text-on-surface">
          ← 주문 내역
        </Link>
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-headline text-on-surface">주문 상세</h1>
          <StatusChip variant={s.variant}>{s.label}</StatusChip>
        </div>
        <p className="text-caption text-on-surface-variant">
          {o.id} · {o.createdAt}
        </p>
      </div>

      {/* 주문 항목 */}
      <Card>
        <CardBody className="flex flex-col gap-3">
          <span className="text-title-m text-on-surface">주문 항목</span>
          {o.items.map((it, i) => (
            <div key={`${it.productId}-${i}`}>
              {i > 0 ? <Divider className="mb-3" /> : null}
              <div className="flex items-center gap-3">
                <div className="size-14 shrink-0 rounded-md" style={{ backgroundImage: "var(--gradient-brand)" }} />
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <span className="line-clamp-1 text-body-l text-on-surface">{it.title}</span>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge>{PRODUCT_TYPE_LABEL[it.type]}</Badge>
                    {it.option ? (
                      <span className="text-caption text-on-surface-variant">{it.option}</span>
                    ) : null}
                    <span className="text-caption text-on-surface-variant">수량 {it.qty}개</span>
                  </div>
                </div>
                <span className="shrink-0 text-title-m tabular-nums text-on-surface">{won(it.price * it.qty)}</span>
              </div>
            </div>
          ))}
        </CardBody>
      </Card>

      {/* 결제 요약 */}
      <Card>
        <CardBody className="flex flex-col gap-2">
          <span className="text-title-m text-on-surface">결제 정보</span>
          <Row label="상품 금액" value={won(o.subtotal)} />
          {o.shipping > 0 ? <Row label="배송비" value={won(o.shipping)} /> : null}
          <Divider className="my-1" />
          <Row label="총 결제금액" value={won(o.total)} strong />
        </CardBody>
      </Card>

      {/* 배송 추적(placeholder) */}
      {o.tracking ? (
        <Card>
          <CardBody className="flex flex-col gap-2">
            <span className="text-title-m text-on-surface">배송 조회</span>
            <Row label="택배사" value={o.tracking.carrier} />
            <Row label="송장번호" value={o.tracking.number} />
            <Button variant="outline" size="sm" className="mt-1 self-start" disabled>
              배송 추적 (준비 중)
            </Button>
          </CardBody>
        </Card>
      ) : null}

      {/* 환불 상태 */}
      {refund ? (
        <Card>
          <CardBody className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-title-m text-on-surface">환불 상태</span>
              <StatusChip variant={refundStatusMeta(refund.status).variant}>
                {refundStatusMeta(refund.status).label}
              </StatusChip>
            </div>
            {refund.reason ? <Row label="사유" value={refund.reason} /> : null}
            {refund.amount != null ? <Row label="환불 금액" value={won(refund.amount)} /> : null}
            <p className="mt-1 text-caption text-on-surface-variant">
              환불은 결제수단 원복 기준 영업일 3~5일 내 처리됩니다. (mock)
            </p>
          </CardBody>
        </Card>
      ) : null}

      {/* 환불 신청 폼 */}
      {canRefund ? (
        <Card>
          <CardBody className="flex flex-col gap-3">
            <span className="text-title-m text-on-surface">환불 신청</span>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="refund-reason" className="text-label text-on-surface">
                환불 사유
              </label>
              <Select value={reason} onValueChange={setReason}>
                <SelectTrigger id="refund-reason" aria-label="환불 사유 선택">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {REFUND_REASONS.map((r) => (
                    <SelectItem key={r} value={r}>
                      {r}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Row label="환불 예정 금액" value={won(o.total)} strong />
            <Button variant="outline" onClick={doRefund} disabled={refundMut.isPending}>
              환불 신청하기
            </Button>
          </CardBody>
        </Card>
      ) : null}

      {/* 주문 취소 */}
      {canCancel ? (
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="ghost" className="self-start text-error">
              주문 취소
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogTitle>주문을 취소할까요?</DialogTitle>
            <DialogDescription>
              {o.id} 주문을 취소하시겠어요? 결제 환급은 데모 환경에서는 실제로 발생하지 않아요.
            </DialogDescription>
            <div className="mt-2 flex justify-end gap-2">
              <DialogClose asChild>
                <Button variant="outline">닫기</Button>
              </DialogClose>
              <DialogClose asChild>
                <Button variant="primary" className="bg-error text-on-error hover:opacity-90" onClick={doCancel}>
                  주문 취소
                </Button>
              </DialogClose>
            </div>
          </DialogContent>
        </Dialog>
      ) : null}
    </div>
  );
}
