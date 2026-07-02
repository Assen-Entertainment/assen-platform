"use client";
import * as React from "react";
import { Card, CardBody, QuantityStepper, RadioGroup, RadioGroupItem, Checkbox, Button, Divider } from "@/components/ui";

/** Checkout — 주문/결제 UI 데모(목업). ※실제 결제/IAP 미연동(결제코드 게이트). */
function won(v: number) {
  return "₩" + v.toLocaleString("ko-KR");
}
function Row({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between text-body-m">
      <span className="text-on-surface-variant">{label}</span>
      <span className="tabular-nums text-on-surface">{won(value)}</span>
    </div>
  );
}

export default function CheckoutPage() {
  const [qty, setQty] = React.useState(1);
  const [pay, setPay] = React.useState("card");
  const [agree, setAgree] = React.useState(false);
  const unit = 18000;
  const shipping = 3000;
  const total = unit * qty + shipping;

  return (
    <main className="min-h-screen bg-surface-container-high py-10">
      <div className="mx-auto flex max-w-lg flex-col gap-4 px-4">
        <h1 className="text-headline text-on-surface">주문 / 결제</h1>

        <Card>
          <CardBody className="flex gap-3">
            <div className="size-20 shrink-0 rounded-md bg-surface-container-high" />
            <div className="flex flex-1 flex-col gap-1">
              <span className="text-title-m text-on-surface">아크릴 스탠드</span>
              <span className="text-body-s text-on-surface-variant">별빛 일러스트</span>
              <div className="mt-1 flex items-center justify-between">
                <QuantityStepper value={qty} onChange={setQty} />
                <span className="text-title-m tabular-nums text-on-surface">{won(unit)}</span>
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="flex flex-col gap-3">
            <span className="text-title-m text-on-surface">결제 수단</span>
            <RadioGroup value={pay} onValueChange={setPay}>
              {[
                ["card", "신용/체크카드"],
                ["bank", "계좌이체"],
                ["pay", "간편결제"],
              ].map(([v, l]) => (
                <div key={v} className="flex items-center gap-2 text-body-m text-on-surface">
                  <RadioGroupItem value={v} id={`pay-${v}`} />
                  <label htmlFor={`pay-${v}`}>{l}</label>
                </div>
              ))}
            </RadioGroup>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="flex flex-col gap-2">
            <Row label="상품금액" value={unit * qty} />
            <Row label="배송비" value={shipping} />
            <Divider className="my-1" />
            <div className="flex items-center justify-between">
              <span className="text-title-m text-on-surface">합계</span>
              <span className="text-title-l tabular-nums text-primary">{won(total)}</span>
            </div>
          </CardBody>
        </Card>

        <label className="flex items-center gap-2 px-1 text-body-s text-on-surface-variant">
          <Checkbox checked={agree} onCheckedChange={(v) => setAgree(v === true)} />
          주문 내용을 확인했으며 결제에 동의합니다
        </label>

        <Button size="lg" disabled={!agree} className="w-full">
          {won(total)} 결제하기
        </Button>
        <p className="text-center text-caption text-on-surface-variant">※ 데모 화면 — 실제 결제 미연동</p>
      </div>
    </main>
  );
}
