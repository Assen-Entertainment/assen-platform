import type { Metadata } from "next";
import Link from "next/link";
import { Badge, DisclaimerNotice } from "@/components/ui";

export const metadata: Metadata = {
  title: "환불정책",
  description: "Assen 환불정책 (법무 검토 전 초안).",
};

const SECTIONS = [
  { h: "제1조 (청약철회)", p: "이용자는 전자상거래법에 따라 결제일 또는 콘텐츠 이용 가능일로부터 7일 이내에 청약철회를 요청할 수 있습니다. 단, 즉시 제공이 개시된 디지털 콘텐츠 등 법령상 예외 항목은 제한될 수 있습니다." },
  { h: "제2조 (환불 절차)", p: "환불 요청은 주문 내역 화면 또는 고객센터를 통해 접수되며, 판매자(크리에이터) 확인을 거쳐 처리 결과가 통지됩니다. 승인 시 결제 수단에 따라 영업일 기준 3~7일 내 환급됩니다." },
  { h: "제3조 (멤버십·정기결제)", p: "멤버십 해지는 다음 결제 예정일 전까지 언제든 가능하며, 해지 시 이미 결제된 이용 기간은 만료일까지 유지됩니다. 일할 환불 기준은 확정 후 명시됩니다." },
  { h: "제4조 (분쟁 처리)", p: "구매자와 판매자 간 분쟁이 발생한 경우 회사는 온라인 분쟁 해결(ODR) 절차에 따라 중재를 지원합니다. 세부 기준과 처리 기한은 확정 후 고지됩니다." },
];

/** 환불정책 — /policy/terms·privacy와 동일 패턴. placeholder 본문 + 법무 검토 전 초안 배지. ※확정 문구는 법무 게이트. */
export default function RefundPolicyPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-5 px-4 py-10">
      <div className="flex items-center gap-2">
        <h1 className="text-headline text-on-surface">환불정책</h1>
        <Badge variant="warning">법무 검토 전 초안</Badge>
      </div>
      <DisclaimerNotice title="초안 안내">
        아래 내용은 데모용 placeholder 초안이며 법적 효력이 없습니다. 최종 정책은 법무 검토를 거쳐 확정·게시됩니다.
      </DisclaimerNotice>
      <div className="flex flex-col gap-5">
        {SECTIONS.map((s) => (
          <section key={s.h} className="flex flex-col gap-1.5">
            <h2 className="text-title-m text-on-surface">{s.h}</h2>
            <p className="text-body-m text-on-surface-variant">{s.p}</p>
          </section>
        ))}
      </div>
      <Link href="/" className="text-body-s text-primary underline underline-offset-2 hover:opacity-80">
        홈으로 돌아가기
      </Link>
    </main>
  );
}
