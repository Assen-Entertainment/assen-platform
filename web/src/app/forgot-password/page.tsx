"use client";
import * as React from "react";
import Link from "next/link";
import { TextField, Button } from "@/components/ui";
import { AuthShell } from "@/components/auth/auth-shell";

/** Forgot Password — W3. 이메일 입력 → 전송(mock) → 완료 상태. ※실 메일 발송 미연동(게이트). */
export default function ForgotPasswordPage() {
  const [email, setEmail] = React.useState("");
  const [sent, setSent] = React.useState(false);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setSent(true); // mock — 실제 재설정 메일 발송 없음(게이트).
  };

  return (
    <AuthShell subtitle="걱정 마세요 — 금방 되돌릴 수 있어요">
        <h2 className="text-title-l text-on-surface">비밀번호 재설정</h2>
        {sent ? (
          <>
            <p className="text-body-m text-on-surface-variant">
              <b className="text-on-surface">{email}</b> 주소로 재설정 링크를 보냈어요. 메일함을 확인해 주세요.
            </p>
            <Button variant="outline" className="w-full" onClick={() => setSent(false)}>
              다른 이메일로 다시 보내기
            </Button>
            <Button className="w-full" asChild>
              <Link href="/login">로그인으로 돌아가기</Link>
            </Button>
          </>
        ) : (
          <form onSubmit={onSubmit} className="flex flex-col gap-4">
            <p className="text-body-s text-on-surface-variant">가입한 이메일을 입력하면 재설정 링크를 보내드려요.</p>
            <TextField
              label="이메일"
              type="email"
              placeholder="you@assen.kr"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <Button type="submit" size="lg" className="w-full" disabled={!email.trim()}>
              재설정 링크 보내기
            </Button>
            <Link href="/login" className="text-center text-caption text-primary underline underline-offset-2 hover:opacity-80">
              로그인으로 돌아가기
            </Link>
          </form>
        )}
        <p className="text-center text-caption text-on-surface-variant">※ 데모 — 실제 메일 발송 미연동(게이트)</p>
    </AuthShell>
  );
}
