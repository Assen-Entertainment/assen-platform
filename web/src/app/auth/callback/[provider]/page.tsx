"use client";
import * as React from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui";
import { AuthShell } from "@/components/auth/auth-shell";
import { useSession } from "@/lib/session";
import { sanitizeNext } from "@/lib/auth-return";

/**
 * 소셜 로그인 콜백 — provider(카카오/Google/Naver)가 code·state와 함께 이 경로로 돌려보낸다.
 * completeSocial(콜백 POST)로 세션을 세우고, startSocial이 sessionStorage에 남긴 복귀 경로로
 * 이동한다. (미들웨어 가드 밖 공개 경로 — 로그인 전 도달 가능해야 함.)
 */
export default function SocialCallbackPage() {
  return (
    <React.Suspense>
      <SocialCallbackContent />
    </React.Suspense>
  );
}

function SocialCallbackContent() {
  const params = useParams<{ provider: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const { completeSocial } = useSession();
  const provider = String(params?.provider ?? "");
  const code = search.get("code") ?? "";
  const state = search.get("state") ?? "";
  const [failed, setFailed] = React.useState(false);
  // 콜백 교환은 마운트당 1회만(React StrictMode 이중 실행/재렌더 방지) — code는 단발성.
  const ran = React.useRef(false);

  React.useEffect(() => {
    if (ran.current || !code) return;
    ran.current = true;
    let next = "/discovery";
    try {
      next = sanitizeNext(sessionStorage.getItem("assen.social.next"));
      sessionStorage.removeItem("assen.social.next");
    } catch {
      /* storage 불가 무시 — 기본 /discovery */
    }
    void (async () => {
      try {
        await completeSocial({ provider, code, state });
        router.replace(next);
      } catch {
        setFailed(true);
      }
    })();
  }, [code, state, provider, completeSocial, router]);

  return (
    <AuthShell subtitle={failed ? undefined : "로그인 중이에요…"}>
      {!code ? (
        <p className="text-center text-body-m text-on-surface-variant">잘못된 접근이에요.</p>
      ) : failed ? (
        <div className="flex flex-col gap-3">
          <p className="text-center text-body-m text-on-surface">소셜 로그인에 실패했어요.</p>
          <Button className="w-full" onClick={() => router.replace("/login")}>
            로그인으로 돌아가기
          </Button>
        </div>
      ) : (
        <p className="text-center text-body-m text-on-surface-variant">잠시만 기다려 주세요…</p>
      )}
    </AuthShell>
  );
}
