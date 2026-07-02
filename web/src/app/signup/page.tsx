"use client";
import * as React from "react";
import { TextField, Button, ConsentGroup } from "@/components/ui";

/** Signup — E6 UI 목업. ※실제 인증·약관 미연동(게이트). */
export default function SignupPage() {
  const [consent, setConsent] = React.useState<string[]>([]);
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
        <Button size="lg" className="w-full">가입하기</Button>
        <p className="text-center text-caption text-on-surface-variant">※ 데모 — 실제 인증·약관 미연동(게이트)</p>
      </div>
    </main>
  );
}
