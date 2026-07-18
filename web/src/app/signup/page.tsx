"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { TextField, Button, ConsentGroup, TextLink } from "@/components/ui";
import { AuthShell } from "@/components/auth/auth-shell";
import { useToast } from "@/components/ui/use-toast";
import { config } from "@/lib/config";
import { ApiError, ERROR_CODES, apiErrorMessage } from "@/lib/api";
import { useSession } from "@/lib/session";
import { sanitizeNext } from "@/lib/auth-return";

/**
 * Signup — 라이브 백엔드면 이메일/비밀번호 가입(B1: 폰 OTP 제거) → 인증 메일 확인, 아니면 mock
 * 즉시 가입(오프라인·데모). ※본인인증은 별도 게이트(가입·열람은 자유, 상호작용/구매만 요구).
 */
export default function SignupPage() {
  // useSearchParams(?next= 복귀)는 Suspense 경계가 필요 → 콘텐츠를 감싼다.
  return (
    <React.Suspense>
      <SignupContent />
    </React.Suspense>
  );
}

function SignupContent() {
  const { useApi } = useSession();
  return useApi ? <EmailSignup /> : <MockSignup />;
}

/** 이메일 가입(라이브). 이메일·비밀번호·닉네임·약관동의 → 가입 → 확인 메일 안내. */
function EmailSignup() {
  const { toast } = useToast();
  const { signupWithEmail } = useSession();
  const searchParams = useSearchParams();
  // 오픈 리다이렉트 방어 — 가입/인증 성공 시 복귀할 경로(login에서 전달).
  const next = sanitizeNext(searchParams.get("next"));
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [nickname, setNickname] = React.useState("");
  const [consent, setConsent] = React.useState<string[]>([]);
  const [busy, setBusy] = React.useState(false);
  const [notice, setNotice] = React.useState<string | null>(null);
  // 가입 성공(확인 메일 발송) 상태 — 값이 문자열이면 확인 화면으로 전환. dev/test에선 verificationToken이
  // 비어있지 않아 "인증 링크 열기(개발용)"로 실제 인박스 없이 플로우를 완결할 수 있다("" on prod).
  const [sentToken, setSentToken] = React.useState<string | null>(null);

  // 만 14세 이상(age14)도 필수(D5) — tos/priv와 함께 확인돼야 가입 가능. 비밀번호는 8자 이상(서버 계약).
  const requiredConsent =
    consent.includes("tos") && consent.includes("priv") && consent.includes("age14");
  const canSubmit =
    email.trim().length > 0 &&
    password.length >= 8 &&
    nickname.trim().length > 0 &&
    requiredConsent &&
    !busy;

  const submit = async () => {
    if (!canSubmit) return;
    setBusy(true);
    setNotice(null);
    try {
      const { verificationToken } = await signupWithEmail({
        email: email.trim(),
        password,
        nickname: nickname.trim(),
        consentTerms: consent.includes("tos"),
        consentPrivacy: consent.includes("priv"),
        ageOver14: consent.includes("age14"),
        marketingConsent: consent.includes("mkt"),
      });
      setSentToken(verificationToken);
    } catch (e) {
      // 계약(안정 code)으로 분기.
      //  · 409 EmailAlreadyRegistered → 로그인 유도.
      //  · 422(ConsentRequired/Underage/InvalidCredentials=비밀번호 길이 등) → 기본 문구 매핑.
      if (e instanceof ApiError && e.status === 409 && e.code === ERROR_CODES.EmailAlreadyRegistered) {
        setNotice("이미 가입된 이메일이에요. 로그인해 주세요.");
      } else if (e instanceof ApiError && e.status === 422) {
        setNotice(apiErrorMessage(e, undefined, "입력값을 확인해 주세요."));
      } else {
        toast({ title: "가입에 실패했어요", description: "잠시 후 다시 시도해 주세요." });
      }
      setBusy(false);
    }
  };

  // 가입 성공 → 확인 메일 안내(+ dev 전용 인증 링크).
  if (sentToken !== null) {
    const devLink =
      config.env !== "production" && sentToken
        ? `/verify-email?token=${encodeURIComponent(sentToken)}${
            next !== "/discovery" ? `&next=${encodeURIComponent(next)}` : ""
          }`
        : null;
    return (
      <AuthShell subtitle="몇 초면 끝나요 — Assen에 오신 걸 환영해요">
        <h2 className="text-title-l text-on-surface">확인 메일을 보냈어요</h2>
        <p className="text-body-s text-on-surface-variant">
          <span className="text-on-surface">{email.trim()}</span> 로 인증 메일을 보냈어요. 받은 메일의
          링크를 눌러 인증을 완료하면 로그인돼요.
        </p>
        {devLink ? (
          <Button asChild size="lg" className="w-full">
            <Link href={devLink}>인증 링크 열기(개발용)</Link>
          </Button>
        ) : null}
        <Link
          href="/login"
          className="text-center text-caption text-primary underline underline-offset-2 hover:opacity-80"
        >
          로그인으로 돌아가기
        </Link>
      </AuthShell>
    );
  }

  return (
    <AuthShell subtitle="몇 초면 끝나요 — Assen에 오신 걸 환영해요">
      <h2 className="text-title-l text-on-surface">회원가입</h2>
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
        autoComplete="new-password"
        placeholder="8자 이상"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        helperText="비밀번호는 8자 이상이어야 해요."
      />
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
          { id: "age14", label: "만 14세 이상입니다", required: true },
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
      {notice ? <p className="text-center text-caption text-error">{notice}</p> : null}
      <Button size="lg" className="w-full" disabled={!canSubmit} onClick={submit}>
        가입하기
      </Button>
      <Link
        href={next !== "/discovery" ? `/login?next=${encodeURIComponent(next)}` : "/login"}
        className="text-center text-caption text-primary underline underline-offset-2 hover:opacity-80"
      >
        이미 계정이 있으신가요? 로그인
      </Link>
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
  const required =
    consent.includes("tos") && consent.includes("priv") && consent.includes("age14");

  const onSignup = () => {
    if (!required) return; // 필수 약관 미동의 시 진행 불가
    signup(); // mock — 실 인증 미연동(게이트)
    router.push(next);
  };

  return (
    <AuthShell subtitle="몇 초면 끝나요 — Assen에 오신 걸 환영해요">
        <h2 className="text-title-l text-on-surface">회원가입</h2>
        {/* 실제 수집 항목과 일치(이메일·비밀번호·닉네임)로 표기. */}
        <TextField label="이메일" type="email" placeholder="you@assen.kr" />
        <TextField label="비밀번호" type="password" placeholder="8자 이상" />
        <TextField label="닉네임" placeholder="사용할 닉네임" />
        <ConsentGroup
          items={[
            { id: "tos", label: "이용약관 동의", required: true },
            { id: "priv", label: "개인정보 처리방침", required: true },
            { id: "age14", label: "만 14세 이상입니다", required: true },
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
