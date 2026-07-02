"use client";
import * as React from "react";
import Link from "next/link";
import { Button, ConsentGroup, Badge } from "@/components/ui";

/** Age Gate — E7 19+ 게이팅 목업. ※실제 본인인증/약관 미연동(대표·법무 게이트). */
export default function AgeGatePage() {
  const [consent, setConsent] = React.useState<string[]>([]);
  const required = ["age", "tos", "priv"];
  const ok = required.every((r) => consent.includes(r));
  return (
    <main className="flex min-h-screen items-center justify-center bg-surface p-4">
      <div className="flex w-full max-w-md flex-col gap-4 rounded-xl border border-outline bg-surface p-6 shadow-2">
        <Badge variant="error" className="self-start">19+</Badge>
        <h1 className="text-headline text-on-surface">성인 콘텐츠 확인</h1>
        <p className="text-body-m text-on-surface-variant">만 19세 이상만 이용할 수 있어요. 아래 항목에 동의 후 입장하세요.</p>
        <ConsentGroup
          items={[
            { id: "age", label: "만 19세 이상입니다", required: true },
            { id: "tos", label: "이용약관 동의", required: true },
            { id: "priv", label: "개인정보 처리방침", required: true },
          ]}
          value={consent}
          onChange={setConsent}
        />
        {ok ? (
          <Button size="lg" className="w-full" asChild>
            <Link href="/discovery">입장</Link>
          </Button>
        ) : (
          <Button size="lg" className="w-full" disabled>
            입장
          </Button>
        )}
        <p className="text-center text-caption text-on-surface-variant">※ 데모 — 실제 본인인증·약관 미연동(게이트)</p>
      </div>
    </main>
  );
}
