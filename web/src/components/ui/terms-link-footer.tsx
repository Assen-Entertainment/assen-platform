import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";

/**
 * TermsLinkFooter — Figma DS(47:16). 약관/개인정보/환불 정책 링크 푸터.
 * 목적지는 정책 페이지(정적, 법무 게이트 본문). 동의 흐름 하단에 배치.
 */
const LINKS = [
  { label: "이용약관", href: "/policy/terms" },
  { label: "개인정보처리방침", href: "/policy/privacy" },
  { label: "환불정책", href: "/policy/refund" },
];

export type TermsLinkFooterProps = React.HTMLAttributes<HTMLElement>;

export function TermsLinkFooter({ className, ...props }: TermsLinkFooterProps) {
  return (
    <nav
      aria-label="정책 링크"
      className={cn("flex flex-wrap items-center gap-x-3 gap-y-1 text-caption text-on-surface-variant", className)}
      {...props}
    >
      {LINKS.map((l, i) => (
        <React.Fragment key={l.href}>
          {i > 0 ? (
            <span aria-hidden className="text-outline">
              ·
            </span>
          ) : null}
          <Link href={l.href} className="underline-offset-2 hover:text-on-surface hover:underline">
            {l.label}
          </Link>
        </React.Fragment>
      ))}
    </nav>
  );
}
