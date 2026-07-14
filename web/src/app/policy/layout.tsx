import type { ReactNode } from "react";
import { SiteFooter } from "@/components/site-footer";

/**
 * 정책 페이지 공통 레이아웃 — 모든 /policy/* 페이지 하단에 사업자 정보(전자상거래법 §10) +
 * 통신판매중개자 고지(§20) 푸터를 노출한다. 페이지 본문(약관/개인정보/환불)은 그대로 두고
 * (승인·초안 구분 유지), 필수 사업자 표시만 공통으로 덧붙인다.
 */
export default function PolicyLayout({ children }: { children: ReactNode }) {
  return (
    <>
      {children}
      <div className="mx-auto w-full max-w-2xl px-4 pb-10">
        <SiteFooter />
      </div>
    </>
  );
}
