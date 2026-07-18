"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui";
import { AuthShell } from "@/components/auth/auth-shell";
import { useToast } from "@/components/ui/use-toast";
import { useSession } from "@/lib/session";
import { sanitizeNext } from "@/lib/auth-return";

/**
 * 이메일 인증 랜딩(B1) — 가입 후 인증 메일 링크(?token=)로 진입한다. 마운트 시 verifyEmail(token)을
 * 1회 호출해 계정을 인증하고 세션(쿠키)을 세운 뒤 복귀 경로로 이동한다. 토큰 부재/무효(400
 * EmailVerificationInvalid)면 안내 + 회원가입 링크. (미들웨어 가드 밖 공개 경로 — 로그인 전 도달.)
 */
export default function VerifyEmailPage() {
  // useSearchParams(?token=/?next=)는 Suspense 경계가 필요 → 콘텐츠를 감싼다.
  return (
    <React.Suspense>
      <VerifyEmailContent />
    </React.Suspense>
  );
}

function VerifyEmailContent() {
  const router = useRouter();
  const { toast } = useToast();
  const search = useSearchParams();
  const { verifyEmail } = useSession();
  const token = search.get("token") ?? "";
  // 오픈 리다이렉트 방어 — 인증 성공 시 복귀할 경로.
  const next = sanitizeNext(search.get("next"));
  // 토큰이 없으면 곧바로 무효 상태(호출 없음). 있으면 검증 중 → 성공(이동)/무효.
  const [invalid, setInvalid] = React.useState(!token);
  // 인증 확인은 마운트당 1회만(StrictMode 이중 실행/재렌더 방지) — 토큰은 단발성.
  const ran = React.useRef(false);

  React.useEffect(() => {
    if (ran.current || !token) return;
    ran.current = true;
    void (async () => {
      try {
        await verifyEmail(token);
        toast({ title: "이메일 인증이 완료됐어요" });
        router.replace(next);
      } catch {
        // 400 EmailVerificationInvalid(위조·만료·불일치) 및 그 외 실패는 무효 안내로 폴백(fail-closed).
        setInvalid(true);
      }
    })();
  }, [token, next, verifyEmail, router, toast]);

  if (invalid) {
    return (
      <AuthShell>
        <div className="flex flex-col gap-3">
          <h2 className="text-center text-title-l text-on-surface">인증에 실패했어요</h2>
          <p className="text-center text-body-m text-on-surface-variant">
            인증 링크가 유효하지 않거나 만료됐어요.
          </p>
          <Button asChild className="w-full">
            <Link href="/signup">회원가입으로 돌아가기</Link>
          </Button>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell subtitle="이메일 인증 중이에요…">
      <p className="text-center text-body-m text-on-surface-variant">잠시만 기다려 주세요…</p>
    </AuthShell>
  );
}
