import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "이용약관",
  description: "Assen 이용약관 (2026-07-12 시행).",
};

const EFFECTIVE_DATE = "2026년 7월 12일";

const SECTIONS: { h: string; p?: string; items?: string[] }[] = [
  {
    h: "제1조 (목적)",
    p: '본 약관은 Assen 서비스를 운영하는 회사(이하 "회사")가 제공하는 크리에이터-팬 플랫폼 서비스(이하 "서비스")의 이용 조건과 절차, 회사와 이용자의 권리·의무 및 책임사항을 규정함을 목적으로 합니다.',
  },
  {
    h: "제2조 (정의)",
    items: [
      '"서비스": 회사가 제공하는 콘텐츠 구독·판매·후원 등 일체의 기능',
      '"이용자": 본 약관에 따라 서비스를 이용하는 회원 및 비회원',
      '"크리에이터": 서비스 내에서 콘텐츠·상품·멤버십을 제공하는 이용자',
      '"팬": 크리에이터의 콘텐츠·상품·멤버십을 이용·후원하는 이용자',
    ],
  },
  {
    h: "제3조 (약관의 효력 및 변경)",
    p: "본 약관은 서비스 화면에 게시하거나 기타의 방법으로 이용자에게 공지함으로써 효력이 발생합니다. 회사는 관계 법령을 위배하지 않는 범위에서 약관을 변경할 수 있으며, 약관을 변경하는 경우 시행일과 변경 사유를 명시하여 시행일 이전에 공지합니다.",
  },
  {
    h: "제4조 (회원가입 및 회원 자격)",
    p: "이용자는 회사가 정한 절차에 따라 회원가입을 신청하며, 회사는 신청 내용을 확인한 후 이를 승낙함으로써 회원가입이 성립합니다. 만 14세 이상인 자만 회원으로 가입할 수 있으며, 일부 성인(19세 이상) 대상 콘텐츠 이용에는 별도의 본인·연령 확인이 필요합니다.",
  },
  {
    h: "제5조 (서비스의 제공 및 변경)",
    p: "회사는 안정적인 서비스 제공을 위해 노력하며, 운영상·기술상 필요에 따라 서비스의 전부 또는 일부를 변경할 수 있습니다. 서비스 내용의 변경 시 회사는 변경 사항을 이용자에게 공지합니다.",
  },
  {
    h: "제6조 (콘텐츠·상품·멤버십의 이용 및 결제)",
    p: "유료 콘텐츠·상품·멤버십의 이용 조건, 가격, 결제 및 정산은 서비스 화면에 표시된 내용과 관계 법령(전자상거래법 등)에 따릅니다. 구체적인 수수료율·정산 주기는 별도 정책 및 서비스 화면을 통해 고지합니다.",
  },
  {
    h: "제7조 (청약철회 및 환불)",
    p: "이용자의 청약철회 및 환불은 전자상거래 등에서의 소비자보호에 관한 법률 등 관계 법령과 회사의 환불정책에 따릅니다. 자세한 내용은 환불정책에서 확인할 수 있습니다.",
  },
  {
    h: "제8조 (회원의 의무 및 금지행위)",
    p: "이용자는 타인의 권리를 침해하거나 법령·공서양속에 위반되는 콘텐츠를 게시하거나 행위를 하여서는 안 됩니다. 이용자가 이를 위반하는 경우 회사는 게시물 삭제, 이용 정지 등의 조치를 취할 수 있습니다.",
  },
  {
    h: "제9조 (회사의 의무)",
    p: "회사는 관계 법령과 본 약관을 준수하며, 이용자의 개인정보를 개인정보 처리방침에 따라 안전하게 보호하기 위해 노력합니다.",
  },
  {
    h: "제10조 (게시물의 관리)",
    p: "이용자가 게시한 콘텐츠가 관계 법령이나 본 약관에 위반되는 경우, 회사는 관계 법령에 따라 해당 게시물에 대한 게시 중단·삭제 등의 조치를 취할 수 있습니다.",
  },
  {
    h: "제11조 (회원 탈퇴 및 이용 제한)",
    p: "이용자는 언제든지 회원 탈퇴를 요청할 수 있으며, 탈퇴 시 개인정보는 개인정보 처리방침에 따라 지체 없이 파기(익명화)됩니다. 다만 관계 법령상 보존 의무가 있는 거래·분쟁 기록은 해당 기간 동안 분리 보관됩니다. 이용자가 본 약관을 위반하는 경우 회사는 이용을 제한하거나 이용계약을 해지할 수 있습니다.",
  },
  {
    h: "제12조 (개인정보의 보호)",
    p: "회사는 이용자의 개인정보를 관계 법령 및 개인정보 처리방침에 따라 보호합니다. 개인정보의 수집·이용·보관·파기에 관한 사항은 개인정보 처리방침에서 정합니다.",
  },
  {
    h: "제13조 (책임의 제한)",
    p: "회사는 천재지변, 이용자의 귀책사유 등 회사의 통제 범위를 벗어난 사유로 인한 서비스 이용 장애에 대하여 관계 법령이 허용하는 범위 내에서 책임을 지지 않습니다.",
  },
  {
    h: "제14조 (준거법 및 관할)",
    p: "본 약관은 대한민국 법령에 따라 규율되고 해석되며, 서비스 이용과 관련하여 회사와 이용자 간에 분쟁이 발생하는 경우 관계 법령이 정한 절차에 따릅니다.",
  },
];

/** 이용약관 — 2026-07-12 시행(법무 승인). */
export default function TermsPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-5 px-4 py-10">
      <h1 className="text-headline text-on-surface">이용약관</h1>
      <p className="text-caption text-on-surface-variant">시행일: {EFFECTIVE_DATE}</p>
      <div className="flex flex-col gap-5">
        {SECTIONS.map((s) => (
          <section key={s.h} className="flex flex-col gap-1.5">
            <h2 className="text-title-m text-on-surface">{s.h}</h2>
            {s.p ? <p className="text-body-m text-on-surface-variant">{s.p}</p> : null}
            {s.items ? (
              <ul className="ml-4 flex list-disc flex-col gap-1 text-body-m text-on-surface-variant">
                {s.items.map((it) => (
                  <li key={it}>{it}</li>
                ))}
              </ul>
            ) : null}
          </section>
        ))}
      </div>
      <p className="text-caption text-on-surface-variant">부칙: 본 약관은 {EFFECTIVE_DATE}부터 시행합니다.</p>
      <div className="flex gap-3">
        <Link href="/policy/privacy" className="text-body-s text-primary underline underline-offset-2 hover:opacity-80">
          개인정보 처리방침
        </Link>
        <Link href="/" className="text-body-s text-primary underline underline-offset-2 hover:opacity-80">
          홈으로 돌아가기
        </Link>
      </div>
    </main>
  );
}
