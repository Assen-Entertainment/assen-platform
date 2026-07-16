"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button, ConsentGroup } from "@/components/ui";
import { AuthShell } from "@/components/auth/auth-shell";
import { useToast } from "@/components/ui/use-toast";
import { useSession } from "@/lib/session";
import { useStartVerify, useConfirmVerify } from "@/lib/api/queries";
import { ApiError } from "@/lib/api";
import { sanitizeNext } from "@/lib/auth-return";

/**
 * 본인인증(KYC) — 미인증 팬이 팔로우·구독·구매 등 게이트 상호작용을 시도하면 전역 VerifyGate가
 * 이 페이지로 유도한다(?next=<원경로>). age-gate와 동일한 verify/start→verify/confirm 흐름을 쓰되
 * 19+ 전용이 아니라 일반 본인인증 프레이밍이다(mock confirm은 kyc+adult 둘 다 세움 — 소프트런치 허용).
 * mock 모드는 즉시 통과(실 검증 아님). 실 provider(PASS/NICE/KCB) 연동은 대표·법무 게이트.
 */
export default function VerifyPage() {
  // useSearchParams(?next= 복귀)는 Suspense 경계가 필요 → 콘텐츠를 감싼다.
  return (
    <React.Suspense>
      <VerifyContent />
    </React.Suspense>
  );
}

function VerifyContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const { user, useApi, markAdultVerified } = useSession();
  const startVerify = useStartVerify();
  const confirmVerify = useConfirmVerify();

  // 오픈 리다이렉트 방어 — 상대경로만 허용(그 외 /discovery). 인증 성공/이미 완료 시 이 경로로 복귀.
  const next = sanitizeNext(searchParams.get("next"));

  const [consent, setConsent] = React.useState<string[]>([]);
  const required = ["identity", "tos", "priv"];
  const ok = required.every((r) => consent.includes(r));
  const pending = startVerify.isPending || confirmVerify.isPending;
  const verified = user?.kycStatus === "verified";

  const verify = async () => {
    if (!ok || pending) return;
    try {
      // 실 경로만 start(mock은 confirm 합성으로 충분). 503=verifier 미배선.
      if (useApi) await startVerify.mutateAsync();
      const result = await confirmVerify.mutateAsync();
      markAdultVerified(result);
      toast({ title: "본인인증이 완료됐어요", description: "이제 팔로우·구독·구매 등 서비스를 이용할 수 있어요." });
      router.push(next);
    } catch (e) {
      if (e instanceof ApiError && e.status === 503) {
        toast({ title: "본인인증 준비 중이에요", description: "잠시 후 다시 시도해 주세요." });
      } else if (!(e instanceof ApiError && e.status === 401)) {
        // 401은 전역 세션 가드가 처리 → 그 외 오류만 안내.
        toast({ title: "인증하지 못했어요", description: "잠시 후 다시 시도해 주세요." });
      }
    }
  };

  return (
    <AuthShell subtitle={null}>
      {verified ? (
        <>
          <h2 className="text-title-l text-on-surface">이미 본인인증이 완료되었어요</h2>
          <p className="text-body-m text-on-surface-variant">
            본인인증이 완료된 계정이에요. 원래 보던 화면으로 돌아갈 수 있어요.
          </p>
          <Button size="lg" className="w-full" asChild>
            <Link href={next}>돌아가기</Link>
          </Button>
        </>
      ) : (
        <>
          <h2 className="text-title-l text-on-surface">본인인증</h2>
          <p className="text-body-m text-on-surface-variant">
            팔로우·구독·구매 등 서비스 이용을 위해 본인인증이 필요해요. 아래 항목에 동의 후 진행해 주세요.
          </p>
          <ConsentGroup
            items={[
              { id: "identity", label: "본인확인 동의", required: true },
              { id: "tos", label: "이용약관 동의", required: true },
              { id: "priv", label: "개인정보 처리방침", required: true },
            ]}
            value={consent}
            onChange={setConsent}
          />
          <Button size="lg" className="w-full" disabled={!ok || pending} onClick={verify}>
            {pending ? "인증 중…" : "본인인증하기"}
          </Button>
          <p className="text-center text-caption text-on-surface-variant">
            ※ 본인인증은 파생 플래그만 저장하며 주민번호·생년월일 원본은 보관하지 않아요.
            {useApi ? "" : " (데모 — 즉시 통과)"}
          </p>
        </>
      )}
    </AuthShell>
  );
}
