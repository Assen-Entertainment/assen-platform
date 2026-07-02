import Link from "next/link";
import { Button } from "@/components/ui";
import { CheckIcon } from "@/lib/icons";

/** 결제 완료 — E5 딜라이트 목업(gradient.brand + 축하). ※실제 결제 미연동(게이트). */
export default function CheckoutComplete() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-surface p-8 text-center">
      <div className="flex size-20 items-center justify-center rounded-full text-white" style={{ backgroundImage: "var(--gradient-brand)" }}>
        <CheckIcon className="size-10" />
      </div>
      <h1 className="text-headline text-on-surface">주문이 완료됐어요!</h1>
      <p className="text-body-m text-on-surface-variant">주문 내역은 마이페이지에서 확인할 수 있어요.</p>
      <div className="mt-2 flex gap-2">
        <Button variant="outline" asChild>
          <Link href="/orders">주문 내역</Link>
        </Button>
        <Button asChild>
          <Link href="/discovery">계속 둘러보기</Link>
        </Button>
      </div>
      <p className="mt-2 text-caption text-on-surface-variant">※ 데모 — 실제 결제 미연동(게이트)</p>
    </main>
  );
}
