"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button, ConsentGroup, Badge } from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { useSession } from "@/lib/session";
import { useStartVerify, useConfirmVerify } from "@/lib/api/queries";
import { ApiError } from "@/lib/api";

/**
 * Age Gate / 성인(19+) 본인인증 뷰 — E7 게이팅.
 * "성인 인증하기" → verify/start → verify/confirm → 세션 반영(markAdultVerified) → 입장.
 * mock 모드는 즉시 통과(실 검증 아님). 실 provider(PASS/NICE/KCB) 연동은 대표·법무 게이트.
 */
export default function AgeGatePage() {
  const router = useRouter();
  const { toast } = useToast();
  const { user, useApi, markAdultVerified } = useSession();
  const startVerify = useStartVerify();
  const confirmVerify = useConfirmVerify();

  const [consent, setConsent] = React.useState<string[]>([]);
  const required = ["age", "tos", "priv"];
  const ok = required.every((r) => consent.includes(r));
  const pending = startVerify.isPending || confirmVerify.isPending;
  const alreadyVerified = user?.adultVerified === true;

  const verify = async () => {
    if (!ok || pending) return;
    try {
      // 실 경로만 start(mock은 confirm 합성으로 충분). 503=verifier 미배선.
      if (useApi) await startVerify.mutateAsync();
      const result = await confirmVerify.mutateAsync();
      markAdultVerified(result);
      toast({ title: "본인인증이 완료되었어요", description: "성인(19+) 콘텐츠를 이용할 수 있어요." });
      router.push("/discovery");
    } catch (e) {
      if (e instanceof ApiError && e.status === 503) {
        toast({ title: "본인인증 준비 중이에요", description: "인증 서비스 연동 전이에요. 잠시 후 다시 시도해 주세요." });
      } else if (!(e instanceof ApiError && e.status === 401)) {
        // 401은 전역 세션 가드가 처리 → 그 외 오류만 안내.
        toast({ title: "인증하지 못했어요", description: "잠시 후 다시 시도해 주세요." });
      }
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-surface p-4">
      <div className="flex w-full max-w-md flex-col gap-4 rounded-xl border border-outline bg-surface p-6 shadow-2">
        <Badge variant="error" className="self-start">19+</Badge>
        <h1 className="text-headline text-on-surface">성인 콘텐츠 확인</h1>
        <p className="text-body-m text-on-surface-variant">만 19세 이상만 이용할 수 있어요. 아래 항목에 동의 후 본인인증을 진행하세요.</p>

        {alreadyVerified ? (
          <>
            <p className="rounded-md border border-success bg-success-container p-3 text-body-s text-on-success-container">
              이미 본인인증이 완료되었어요.
            </p>
            <Button size="lg" className="w-full" asChild>
              <Link href="/discovery">입장</Link>
            </Button>
          </>
        ) : (
          <>
            <ConsentGroup
              items={[
                { id: "age", label: "만 19세 이상입니다", required: true },
                { id: "tos", label: "이용약관 동의", required: true },
                { id: "priv", label: "개인정보 처리방침", required: true },
              ]}
              value={consent}
              onChange={setConsent}
            />
            <Button size="lg" className="w-full" disabled={!ok || pending} onClick={verify}>
              {pending ? "인증 중…" : "성인 인증하기"}
            </Button>
            <p className="text-center text-caption text-on-surface-variant">
              ※ 본인인증은 파생 플래그(성인 여부)만 저장하며 주민번호·생년월일 원본은 보관하지 않아요.
              {useApi ? "" : " (데모 — 즉시 통과)"}
            </p>
          </>
        )}
      </div>
    </main>
  );
}
