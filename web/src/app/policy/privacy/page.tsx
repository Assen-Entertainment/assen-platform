import type { Metadata } from "next";
import Link from "next/link";
import { Badge, DisclaimerNotice } from "@/components/ui";

export const metadata: Metadata = {
  title: "개인정보 처리방침",
  description: "Assen 개인정보 처리방침 (법무 검토 전 초안).",
};

const SECTIONS = [
  { h: "1. 수집하는 개인정보 항목", p: "회원가입·서비스 이용 과정에서 이메일, 닉네임, 결제 정보 등이 수집될 수 있습니다. 구체적 수집 항목과 범위는 확정 후 명시됩니다." },
  { h: "2. 개인정보의 수집 및 이용 목적", p: "회원 관리, 콘텐츠·상품 제공, 결제 및 정산, 고객 문의 대응, 서비스 개선을 위해 개인정보를 이용합니다." },
  { h: "3. 개인정보의 보유 및 이용 기간", p: "원칙적으로 이용 목적 달성 시 지체 없이 파기하며, 관련 법령이 정한 기간 동안 보관이 필요한 정보는 해당 기간 동안 보관합니다." },
  { h: "4. 개인정보의 제3자 제공", p: "이용자의 동의가 있거나 법령에 근거가 있는 경우를 제외하고 개인정보를 외부에 제공하지 않습니다. 결제 처리를 위한 PG사 위탁 등 세부 사항은 확정 후 고지됩니다." },
  { h: "5. 이용자의 권리", p: "이용자는 언제든지 자신의 개인정보를 조회·수정하거나 처리 정지·삭제를 요청할 수 있습니다. 관련 문의는 고객센터를 통해 접수할 수 있습니다." },
];

/** 개인정보 처리방침 — W3. placeholder 본문 + 법무 검토 전 초안 배지. ※확정 문구는 법무 게이트. */
export default function PrivacyPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-5 px-4 py-10">
      <div className="flex items-center gap-2">
        <h1 className="text-headline text-on-surface">개인정보 처리방침</h1>
        <Badge variant="warning">법무 검토 전 초안</Badge>
      </div>
      <DisclaimerNotice title="초안 안내">
        아래 내용은 데모용 placeholder 초안이며 법적 효력이 없습니다. 최종 방침은 법무 검토를 거쳐 확정·게시됩니다.
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
