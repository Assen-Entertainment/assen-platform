"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { TextField, Button, Divider } from "@/components/ui";
import { AuthShell } from "@/components/auth/auth-shell";
import { SocialButtons } from "@/components/auth/social-buttons";
import { useToast } from "@/components/ui/use-toast";
import { ApiError, ERROR_CODES } from "@/lib/api";
import { useSession } from "@/lib/session";
import { sanitizeNext } from "@/lib/auth-return";

/**
 * Login — 라이브 백엔드면 이메일/비밀번호 + 소셜 로그인(B1: 폰 OTP 제거), 아니면 mock 즉시
 * 로그인(오프라인·데모). ※본인인증은 별도 게이트(상호작용/구매만 요구, 열람은 자유).
 */
export default function LoginPage() {
  // useSearchParams(?next= 복귀)는 Suspense 경계가 필요 → 콘텐츠를 감싼다.
  return (
    <React.Suspense>
      <LoginContent />
    </React.Suspense>
  );
}

function LoginContent() {
  const { useApi } = useSession();
  const searchParams = useSearchParams();
  // 오픈 리다이렉트 방어 — 상대경로만 허용(그 외 기본값). 로그인/가입 성공 시 이 경로로 복귀.
  const next = sanitizeNext(searchParams.get("next"));
  return useApi ? <EmailLogin next={next} /> : <MockLogin next={next} />;
}

/** 이메일 로그인(라이브). 이메일 + 비밀번호 → 로그인, 또는 소셜 계속하기. */
function EmailLogin({ next }: { next: string }) {
  const router = useRouter();
  const { toast } = useToast();
  const { loginWithEmail, startSocial } = useSession();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [notice, setNotice] = React.useState<string | null>(null);

  const canSubmit = email.trim().length > 0 && password.length > 0 && !busy;

  const submit = async () => {
    if (!canSubmit) return;
    setBusy(true);
    setNotice(null);
    try {
      await loginWithEmail(email.trim(), password);
      router.push(next);
    } catch (e) {
      // 계약(안정 code)으로 분기 — 문자열 매칭 없음.
      //  · 422 InvalidCredentials → 이메일·비밀번호 오류(비구분 안내).
      //  · 403 EmailNotVerified → 인증 메일 링크로 인증 유도.
      //  · 그 외는 토스트 폴백.
      if (e instanceof ApiError && e.status === 422 && e.code === ERROR_CODES.InvalidCredentials) {
        setNotice("이메일 또는 비밀번호가 올바르지 않아요.");
      } else if (e instanceof ApiError && e.status === 403 && e.code === ERROR_CODES.EmailNotVerified) {
        setNotice("이메일 인증이 필요해요. 받은 메일의 링크로 인증을 완료해 주세요.");
      } else {
        toast({ title: "로그인에 실패했어요", description: "잠시 후 다시 시도해 주세요." });
      }
      setBusy(false);
    }
  };

  // 회원가입 링크 — 복귀 경로(next)를 함께 전달(가입 후에도 원경로 복귀).
  const signupHref = next !== "/discovery" ? `/signup?next=${encodeURIComponent(next)}` : "/signup";

  return (
    <AuthShell>
      <TextField
        label="이메일"
        type="email"
        autoComplete="email"
        placeholder="you@assen.kr"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <TextField
        label="비밀번호"
        type="password"
        autoComplete="current-password"
        placeholder="••••••••"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") void submit();
        }}
      />
      {notice ? <p className="text-center text-caption text-error">{notice}</p> : null}
      <Button size="lg" className="w-full" disabled={!canSubmit} onClick={submit}>
        로그인
      </Button>

      <div className="flex items-center gap-2">
        <Divider className="flex-1" />
        <span className="shrink-0 text-caption text-on-surface-variant">또는</span>
        <Divider className="flex-1" />
      </div>
      <SocialButtons onProvider={(provider) => void startSocial(provider, next)} disabled={busy} />
      <Link
        href={signupHref}
        className="text-center text-caption text-primary underline underline-offset-2 hover:opacity-80"
      >
        처음이신가요? 회원가입
      </Link>
      <p className="text-center text-caption text-on-surface-variant">
        계속하면{" "}
        <Link href="/policy/terms" className="text-primary underline underline-offset-2">이용약관</Link>
        {" 및 "}
        <Link href="/policy/privacy" className="text-primary underline underline-offset-2">개인정보처리방침</Link>
        에 동의하고 만 14세 이상임을 확인합니다.
      </p>
    </AuthShell>
  );
}

/** mock 로그인(오프라인·데모) — 기존 UI 목업 유지. ※실 인증 미연동(게이트). */
function MockLogin({ next }: { next: string }) {
  const router = useRouter();
  const { login } = useSession();

  const onLogin = () => {
    login(); // mock — 실 크리덴셜 미검증(게이트)
    router.push(next);
  };

  return (
    <AuthShell>
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
    </AuthShell>
  );
}
