"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { TextField, Button, ConsentGroup, TextLink, OTPInput } from "@/components/ui";
import { AuthShell } from "@/components/auth/auth-shell";
import { useToast } from "@/components/ui/use-toast";
import { config } from "@/lib/config";
import { useSession } from "@/lib/session";
import { sanitizeNext } from "@/lib/auth-return";

/**
 * Signup — 라이브 백엔드면 전화번호 OTP 2단계 가입, 아니면 mock 즉시 가입(오프라인·데모).
 * ※본인인증/실 크리덴셜은 게이트. OTP는 dev에서 문자 대신 고정 인증번호를 사용한다.
 */
export default function SignupPage() {
  // useSearchParams(?phone= prefill)는 Suspense 경계가 필요 → 콘텐츠를 감싼다.
  return (
    <React.Suspense>
      <SignupContent />
    </React.Suspense>
  );
}

function SignupContent() {
  const { useApi } = useSession();
  return useApi ? <OtpSignup /> : <MockSignup />;
}

/** OTP 가입(라이브). 전화번호 → 인증번호 받기 → 인증번호·닉네임·약관동의 → 가입. */
function OtpSignup() {
  const router = useRouter();
  const { toast } = useToast();
  const { requestOtp, signupWithOtp } = useSession();
  const searchParams = useSearchParams();
  // 오픈 리다이렉트 방어 — 가입 성공 시 복귀할 경로(login에서 전달).
  const next = sanitizeNext(searchParams.get("next"));
  // login에서 넘어온 ?phone= 을 초기값으로 자동 입력(이후 사용자가 편집 가능).
  const [phone, setPhone] = React.useState(() => searchParams.get("phone") ?? "");
  const [otp, setOtp] = React.useState("");
  const [nickname, setNickname] = React.useState("");
  const [consent, setConsent] = React.useState<string[]>([]);
  const [step, setStep] = React.useState<"phone" | "form">("phone");
  const [busy, setBusy] = React.useState(false);
  const requiredConsent = consent.includes("tos") && consent.includes("priv");
  const canSubmit = otp.length >= 6 && nickname.trim().length > 0 && requiredConsent && !busy;

  const sendOtp = async () => {
    if (!phone.trim() || busy) return;
    setBusy(true);
    try {
      await requestOtp(phone.trim());
      setStep("form");
      toast({ title: "인증번호를 보냈어요", description: "문자로 받은 인증번호를 입력해 주세요." });
    } catch {
      toast({ title: "인증번호 발송에 실패했어요", description: "전화번호를 확인하고 다시 시도해 주세요." });
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    if (!canSubmit) return;
    setBusy(true);
    try {
      await signupWithOtp({
        phone: phone.trim(),
        otp,
        nickname: nickname.trim(),
        consentTerms: true,
        consentPrivacy: true,
      });
      router.push(next);
    } catch {
      toast({ title: "가입에 실패했어요", description: "인증번호를 확인하고 다시 시도해 주세요." });
      setBusy(false);
    }
  };

  return (
    <AuthShell subtitle="몇 초면 끝나요 — Assen에 오신 걸 환영해요">
        <h2 className="text-title-l text-on-surface">회원가입</h2>

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
            <Link href="/login" className="text-center text-caption text-primary underline underline-offset-2 hover:opacity-80">
              이미 계정이 있으신가요? 로그인
            </Link>
          </>
        ) : (
          <>
            <p className="text-body-s text-on-surface-variant">
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
            <TextField
              label="닉네임"
              placeholder="사용할 닉네임"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              maxLength={20}
            />
            <ConsentGroup
              items={[
                { id: "tos", label: "이용약관 동의", required: true },
                { id: "priv", label: "개인정보 처리방침", required: true },
                { id: "mkt", label: "마케팅 수신(선택)" },
              ]}
              value={consent}
              onChange={setConsent}
            />
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
            <Button size="lg" className="w-full" disabled={!canSubmit} onClick={submit}>
              가입하기
            </Button>
          </>
        )}
    </AuthShell>
  );
}

/** mock 가입(오프라인·데모) — 기존 UI 목업 유지. ※실 인증·약관 미연동(게이트). */
function MockSignup() {
  const router = useRouter();
  const { signup } = useSession();
  const searchParams = useSearchParams();
  const next = sanitizeNext(searchParams.get("next"));
  const [consent, setConsent] = React.useState<string[]>([]);
  const required = consent.includes("tos") && consent.includes("priv");

  const onSignup = () => {
    if (!required) return; // 필수 약관 미동의 시 진행 불가
    signup(); // mock — 실 인증 미연동(게이트)
    router.push(next);
  };

  return (
    <AuthShell subtitle="몇 초면 끝나요 — Assen에 오신 걸 환영해요">
        <h2 className="text-title-l text-on-surface">회원가입</h2>
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
    </AuthShell>
  );
}
