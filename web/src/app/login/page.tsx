"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { TextField, Button, Divider } from "@/components/ui";
import { useSession } from "@/lib/session";

/** Login — E6 UI 목업. ※실제 인증/본인인증 미연동(대표·법무 게이트). mock 세션만 기록. */
export default function LoginPage() {
  const router = useRouter();
  const { login } = useSession();

  const onLogin = () => {
    login(); // mock — 실 크리덴셜 미검증(게이트)
    router.push("/discovery");
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-surface-container-high p-4">
      <div className="flex w-full max-w-sm flex-col gap-4 rounded-xl bg-surface p-6 shadow-2">
        <h1 className="text-center text-display-m text-primary">Assen</h1>
        <p className="text-center text-body-s text-on-surface-variant">크리에이터의 세계관을 팬과 잇는 무대</p>
        <TextField label="이메일" type="email" placeholder="you@assen.kr" />
        <TextField label="비밀번호" type="password" placeholder="••••••••" />
        <Button size="lg" className="w-full" onClick={onLogin}>로그인</Button>
        <Link href="/forgot-password" className="text-center text-caption text-primary underline underline-offset-2 hover:opacity-80">비밀번호를 잊으셨나요?</Link>
        <div className="flex items-center gap-2">
          <Divider className="flex-1" />
          <span className="shrink-0 text-caption text-on-surface-variant">또는</span>
          <Divider className="flex-1" />
        </div>
        <div className="flex flex-col gap-2">
          <Button variant="outline" className="w-full" onClick={onLogin}>카카오로 계속</Button>
          <Button variant="outline" className="w-full" onClick={onLogin}>Google로 계속</Button>
        </div>
        <p className="text-center text-caption text-on-surface-variant">※ 데모 — 실제 인증·본인인증 미연동(게이트)</p>
      </div>
    </main>
  );
}
