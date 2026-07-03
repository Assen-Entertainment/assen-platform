"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { TextField, Button, ConsentGroup, TextLink } from "@/components/ui";
import { useSession } from "@/lib/session";

/** Signup — E6 UI 목업. ※실제 인증·약관 미연동(게이트). mock 세션만 기록. */
export default function SignupPage() {
  const router = useRouter();
  const { signup } = useSession();
  const [consent, setConsent] = React.useState<string[]>([]);
  const required = consent.includes("tos") && consent.includes("priv");

  const onSignup = () => {
    if (!required) return; // 필수 약관 미동의 시 진행 불가
    signup(); // mock — 실 인증 미연동(게이트)
    router.push("/discovery");
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-surface-container-high p-4">
      <div className="flex w-full max-w-sm flex-col gap-4 rounded-xl bg-surface p-6 shadow-2">
        <h1 className="text-title-l text-on-surface">회원가입</h1>
        <TextField label="이름" placeholder="홍길동" />
        <TextField label="이메일" type="email" placeholder="you@assen.kr" />
        <TextField label="비밀번호" type="password" placeholder="••••••••" />
        <ConsentGroup
          items={[
            { id: "tos", label: "이용약관 동의", required: true },
            { id: "priv", label: "개인정보 처리방침", required: true },
            { id: "mkt", label: "마케팅 수신(선택)" },
          ]}
          value={consent}
          onChange={setConsent}
        />
        {/* 동의 항목 전문 링크 — 체크 로직과 분리(라벨 클릭=토글 보존). */}
        <p className="text-caption text-on-surface-variant">
          전문 보기:{" "}
          <TextLink asChild className="text-caption">
            <Link href="/policy/terms">이용약관</Link>
          </TextLink>
          {" · "}
          <TextLink asChild className="text-caption">
            <Link href="/policy/privacy">개인정보 처리방침</Link>
          </TextLink>
        </p>
        <Button size="lg" className="w-full" disabled={!required} onClick={onSignup}>가입하기</Button>
        <p className="text-center text-caption text-on-surface-variant">※ 데모 — 실제 인증·약관 미연동(게이트)</p>
      </div>
    </main>
  );
}
