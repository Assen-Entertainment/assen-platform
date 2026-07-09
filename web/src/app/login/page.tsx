"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { TextField, Button, Divider, OTPInput } from "@/components/ui";
import { AuthShell } from "@/components/auth/auth-shell";
import { useToast } from "@/components/ui/use-toast";
import { config } from "@/lib/config";
import { ApiError, ERROR_CODES } from "@/lib/api";
import { useSession } from "@/lib/session";
import { sanitizeNext } from "@/lib/auth-return";

/**
 * Login — 라이브 백엔드면 전화번호 OTP 2단계 재인증, 아니면 mock 즉시 로그인(오프라인·데모).
 * ※본인인증/실 크리덴셜은 게이트. OTP는 dev에서 문자 대신 고정 인증번호를 사용한다.
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
  return useApi ? <OtpLogin next={next} /> : <MockLogin next={next} />;
}

/** OTP 로그인(라이브). 전화번호 → 인증번호 받기 → 인증번호 입력 → 로그인. */
function OtpLogin({ next }: { next: string }) {
  const router = useRouter();
  const { toast } = useToast();
  const { requestOtp, loginWithOtp } = useSession();
  const [phone, setPhone] = React.useState("");
  const [otp, setOtp] = React.useState("");
  const [step, setStep] = React.useState<"phone" | "otp">("phone");
  const [busy, setBusy] = React.useState(false);
  const [notice, setNotice] = React.useState<string | null>(null);

  const sendOtp = async () => {
    if (!phone.trim() || busy) return;
    setBusy(true);
    setNotice(null);
    try {
      await requestOtp(phone.trim());
      setStep("otp");
      toast({ title: "인증번호를 보냈어요", description: "문자로 받은 인증번호를 입력해 주세요." });
    } catch {
      toast({ title: "인증번호 발송에 실패했어요", description: "전화번호를 확인하고 다시 시도해 주세요." });
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    if (otp.length < 6 || busy) return;
    setBusy(true);
    setNotice(null);
    try {
      await loginWithOtp(phone.trim(), otp);
      router.push(next);
    } catch (e) {
      // 422는 미가입·인증번호 오류가 섞여 온다 — 서버 error code로 구분한다(문자열 부분일치 제거).
      //  · code=AccountNotRegistered → 회원가입 유도(미가입 번호).
      //  · code=OtpInvalid → 인증번호 오류 안내.
      //  · 그 외 422는 서버 detail(표시용)로 폴백.
      if (e instanceof ApiError && e.status === 422) {
        if (e.code === ERROR_CODES.AccountNotRegistered) {
          setNotice("가입되지 않은 번호예요. 아래에서 회원가입을 진행해 주세요.");
        } else if (e.code === ERROR_CODES.OtpInvalid) {
          setNotice("인증번호가 올바르지 않아요. 다시 확인해 주세요.");
        } else {
          setNotice(e.detail ?? "인증번호가 올바르지 않아요. 다시 확인해 주세요.");
        }
      } else {
        toast({ title: "로그인에 실패했어요", description: "인증번호를 확인하고 다시 시도해 주세요." });
      }
      setBusy(false);
    }
  };

  // 회원가입 링크 — 입력한 전화번호와 복귀 경로(next)를 함께 전달(가입 후에도 원경로 복귀).
  const signupParams = new URLSearchParams();
  if (phone.trim()) signupParams.set("phone", phone.trim());
  if (next !== "/discovery") signupParams.set("next", next);
  const signupHref = signupParams.toString() ? `/signup?${signupParams}` : "/signup";

  return (
    <AuthShell>
        {step === "phone" ? (
          <>
            <TextField
              label="휴대폰 번호"
              type="tel"
              inputMode="numeric"
              placeholder="01012345678"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
            <Button size="lg" className="w-full" disabled={!phone.trim() || busy} onClick={sendOtp}>
              인증번호 받기
            </Button>
          </>
        ) : (
          <>
            <p className="text-center text-body-s text-on-surface-variant">
              <span className="text-on-surface">{phone}</span> 로 보낸 인증번호를 입력하세요
            </p>
            <div className="flex justify-center">
              <OTPInput value={otp} onChange={setOtp} />
            </div>
            {config.env !== "production" ? (
              <p className="text-center text-caption text-on-surface-variant">
                개발 환경에서는 문자 대신 고정 인증번호가 사용됩니다.
              </p>
            ) : null}
            {notice ? (
              <p className="text-center text-caption text-error">{notice}</p>
            ) : null}
            <Button size="lg" className="w-full" disabled={otp.length < 6 || busy} onClick={submit}>
              로그인
            </Button>
            <button
              type="button"
              className="text-center text-caption text-primary underline underline-offset-2 hover:opacity-80"
              onClick={() => {
                setStep("phone");
                setOtp("");
                setNotice(null);
              }}
            >
              전화번호 다시 입력
            </button>
          </>
        )}

        <div className="flex items-center gap-2">
          <Divider className="flex-1" />
          <span className="shrink-0 text-caption text-on-surface-variant">또는</span>
          <Divider className="flex-1" />
        </div>
        <Link
          href={signupHref}
          className="text-center text-caption text-primary underline underline-offset-2 hover:opacity-80"
        >
          처음이신가요? 회원가입
        </Link>
        <p className="text-center text-caption text-on-surface-variant">
          ※ 소셜·이메일 로그인은 준비 중이에요.
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
