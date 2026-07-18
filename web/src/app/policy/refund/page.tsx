import type { Metadata } from "next";
import Link from "next/link";
import { Badge, DisclaimerNotice } from "@/components/ui";

export const metadata: Metadata = {
  title: "환불정책",
  description: "Assen 환불정책 (법무 검토 전 초안).",
};

// MVP(디지털 상품 단건 구매·통신판매중개) 기준 초안. 근거 법령을 조문 단위로 반영하되,
// 최종 문구·청약철회 제한 고지의 구체 표현은 법무 검토·확정 사항.
const SECTIONS = [
  { h: "제1조 (청약철회)", p: "이용자는 「전자상거래 등에서의 소비자보호에 관한 법률」 제17조에 따라, 계약체결일 또는 콘텐츠 이용이 가능해진 날 중 나중의 날부터 7일 이내에 청약철회를 요청할 수 있습니다." },
  { h: "제2조 (디지털 콘텐츠의 청약철회 제한)", p: "이용 또는 다운로드가 개시된 디지털 콘텐츠 등 법령이 정한 경우에는 청약철회가 제한될 수 있습니다. 회사와 판매자(크리에이터)는 청약철회가 제한되는 콘텐츠에 대하여 구매 전 그 사실을 명확히 고지하며, 이러한 고지·조치가 없는 경우 청약철회는 제한되지 않습니다." },
  { h: "제3조 (환불 및 대금의 환급)", p: "청약철회가 수락되면 관계 법령(같은 법 제18조)에 따라 원칙적으로 3영업일 이내에 결제수단에 따라 대금을 환급합니다. 결제대행사·카드사 등의 사정에 따라 실제 환급까지 추가 기간이 소요될 수 있습니다." },
  { h: "제4조 (환불 절차)", p: "환불 요청은 주문 내역 화면 또는 고객센터를 통해 접수되며, 통신판매중개자인 회사는 판매자(크리에이터)와 구매자 간 청약철회·환불의 처리를 중개·지원합니다. 접수된 요청은 판매자 확인을 거쳐 처리 결과가 통지됩니다." },
  { h: "제5조 (통신판매중개자의 지위 및 책임)", p: "회사는 통신판매중개자로서 통신판매의 당사자가 아니며, 개별 상품·거래의 당사자는 판매자(크리에이터)입니다. 상품·거래 및 환불에 관한 책임은 관계 법령이 정한 범위에서 판매자에게 있으며, 회사는 분쟁 발생 시 그 해결을 지원합니다." },
  { h: "제6조 (분쟁 처리)", p: "구매자와 판매자 간 분쟁이 발생한 경우, 이용자는 소비자분쟁조정위원회(전자상거래) 등 관계 기관을 통해 분쟁 조정을 신청할 수 있으며 회사는 이에 협조합니다." },
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
