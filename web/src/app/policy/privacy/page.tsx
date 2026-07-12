import type { Metadata } from "next";
import Link from "next/link";
import { Badge, DisclaimerNotice } from "@/components/ui";

export const metadata: Metadata = {
  title: "개인정보 처리방침",
  description: "Assen 개인정보 처리방침 (법무 검토 전 초안).",
};

const SECTIONS = [
  { h: "1. 수집하는 개인정보 항목", p: "회원가입 시 휴대전화번호(본인인증용 — 원본은 저장하지 않고 가명처리된 해시값으로만 보관)와 닉네임(표시용)을 수집하며, 서비스 이용 과정에서 접속기록(IP·기기·요청 식별자)이 자동 생성됩니다. 생년월일·주민등록번호·계좌/카드 정보는 저장하지 않습니다." },
  { h: "2. 개인정보의 수집 및 이용 목적", p: "회원 식별·인증, 콘텐츠·서비스 제공, 부정이용 방지 및 보안, 고객 문의 대응을 위해 개인정보를 이용합니다." },
  { h: "3. 개인정보의 보유 및 이용 기간", p: "회원 탈퇴 시 지체 없이 파기(익명화)합니다. 다만 관계 법령상 보존 의무가 있는 거래·분쟁 기록은 해당 기간(전자상거래법: 계약·결제 기록 5년, 소비자 분쟁 기록 3년) 동안 분리 보관 후 파기하며, 접속기록은 3개월간 보관합니다." },
  { h: "4. 개인정보의 제3자 제공", p: "이용자의 동의가 있거나 법령에 근거가 있는 경우를 제외하고 개인정보를 외부에 제공하지 않습니다. 배송 상품 판매나 실 결제 도입 시 택배사·PG사 등에 대한 제공 항목·목적을 사전에 고지하고 별도 동의를 받습니다." },
  { h: "5. 이용자의 권리", p: "이용자는 언제든지 자신의 개인정보를 조회·수정하거나 처리 정지·삭제(회원 탈퇴)를 요청할 수 있습니다. 관련 문의는 고객센터를 통해 접수할 수 있습니다." },
  { h: "6. 가입 연령", p: "만 14세 이상만 회원으로 가입할 수 있습니다." },
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
