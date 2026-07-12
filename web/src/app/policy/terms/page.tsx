import type { Metadata } from "next";
import Link from "next/link";
import { Badge, DisclaimerNotice } from "@/components/ui";

export const metadata: Metadata = {
  title: "이용약관",
  description: "Assen 이용약관 (법무 검토 전 초안).",
};

const SECTIONS = [
  { h: "제1조 (목적)", p: "본 약관은 Assen(이하 '회사')이 제공하는 크리에이터-팬 플랫폼 서비스의 이용 조건과 절차, 회사와 이용자의 권리·의무 및 책임사항을 규정함을 목적으로 합니다." },
  { h: "제2조 (정의)", p: "'서비스'란 회사가 제공하는 콘텐츠 구독·판매·후원 등 일체의 기능을 말합니다. '크리에이터'와 '팬'의 정의 및 세부 이용 조건은 확정 후 명시됩니다." },
  { h: "제3조 (약관의 효력 및 변경)", p: "본 약관은 서비스 화면에 게시하거나 기타의 방법으로 이용자에게 공지함으로써 효력이 발생합니다. 회사는 관련 법령을 위배하지 않는 범위에서 약관을 변경할 수 있습니다." },
  { h: "제4조 (콘텐츠 및 결제)", p: "유료 콘텐츠·상품·멤버십의 결제, 환불, 정산 조건은 별도 정책 및 관련 법령(전자상거래법 등)에 따릅니다. 구체적 수수료율·정산 주기는 확정 후 고지됩니다." },
  { h: "제5조 (금지행위)", p: "이용자는 타인의 권리를 침해하거나 법령·공서양속에 위반되는 콘텐츠를 게시할 수 없습니다. 위반 시 게시 제한·이용 정지 등의 조치가 취해질 수 있습니다." },
  { h: "제6조 (회원 자격 및 연령)", p: "만 14세 이상인 자만 회원으로 가입할 수 있습니다. 일부 성인(19세 이상) 대상 콘텐츠 이용에는 별도의 본인·연령 확인이 필요합니다." },
  { h: "제7조 (회원 탈퇴)", p: "이용자는 언제든지 회원 탈퇴를 요청할 수 있으며, 탈퇴 시 개인정보는 개인정보 처리방침에 따라 지체 없이 파기(익명화)됩니다. 관계 법령상 보존 의무가 있는 거래·분쟁 기록은 해당 기간 동안 분리 보관됩니다." },
];

/** 이용약관 — W3. placeholder 본문 + 법무 검토 전 초안 배지. ※확정 문구는 법무 게이트. */
export default function TermsPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-5 px-4 py-10">
      <div className="flex items-center gap-2">
        <h1 className="text-headline text-on-surface">이용약관</h1>
        <Badge variant="warning">법무 검토 전 초안</Badge>
      </div>
      <DisclaimerNotice title="초안 안내">
        아래 내용은 데모용 placeholder 초안이며 법적 효력이 없습니다. 최종 약관은 법무 검토를 거쳐 확정·게시됩니다.
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
