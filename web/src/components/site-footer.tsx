import { TermsLinkFooter } from "@/components/ui";
import { COMPANY } from "@/lib/company";

/**
 * SiteFooter — 전자상거래법 §10(사업자 정보 표시) + §20(통신판매중개자 고지) 공통 푸터.
 *
 * 사실 정보는 {@link COMPANY}(이용약관 제15조 승인본과 동일)에서 오며, 통신판매업 신고번호는
 * 진행 중이라 "준비 중"으로 표기한다(발급 시 lib/company에서 교체). 통신판매중개자 면책은
 * 다중 크리에이터 마켓플레이스의 사실적 지위 고지(§20)로, 법률 문구 창작이 아니라 회사의
 * 역할을 명시하는 표준 고지다. 정책 링크는 DS {@link TermsLinkFooter}를 합성한다.
 */
export function SiteFooter() {
  return (
    <footer className="mt-10 flex flex-col gap-3 border-t border-outline pt-6 text-caption text-on-surface-variant">
      <TermsLinkFooter />
      <p>
        {COMPANY.name} · 대표 {COMPANY.ceo} · 사업자등록번호{" "}
        {COMPANY.businessNumber} · 통신판매업 신고{" "}
        {COMPANY.mailOrderNumber ?? "준비 중"}
      </p>
      <p>{COMPANY.address}</p>
      <p>문의: {COMPANY.contact}</p>
      <p>
        회사는 통신판매중개자로서 통신판매의 당사자가 아니며, 개별 상품·거래의
        당사자는 판매자(크리에이터)입니다. 상품·거래에 관한 정보와 책임은 해당
        판매자에게 있습니다.
      </p>
    </footer>
  );
}
