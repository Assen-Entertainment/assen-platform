"use client";
import * as React from "react";
import { usePathname, useRouter } from "next/navigation";
import { Button, Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui";
import { subscribeVerifyRequired } from "@/lib/verify-gate";

/**
 * VerifyGate — 미인증 팬이 게이트 상호작용(팔로우·구독·구매 등)을 시도해 서버가 403
 * (IdentityVerificationRequired)을 낼 때, 전역 MutationCache가 방출한 신호를 받아 뜨는 안내
 * 다이얼로그. 루트 레이아웃에 단 한 번 마운트되어 어떤 페이지 위에도 오버레이된다(원시 실패 대신
 * 본인인증 유도). "본인인증하기" → /verify?next=<현재경로>로 이동, "다음에" → 닫기.
 * 신호가 중복돼도 이미 열려 있으면 setOpen(true) 멱등으로 무시된다.
 */
export function VerifyGate() {
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = React.useState(false);

  // 마운트 시 구독, 언마운트 시 해제. 신호가 오면 다이얼로그를 연다.
  React.useEffect(() => subscribeVerifyRequired(() => setOpen(true)), []);

  const goVerify = () => {
    setOpen(false);
    router.push(`/verify?next=${encodeURIComponent(pathname ?? "/discovery")}`);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogTitle>본인인증이 필요해요</DialogTitle>
        <DialogDescription>
          팔로우·구독·구매 등 서비스 이용을 위해 본인인증이 필요해요.
        </DialogDescription>
        <div className="mt-2 flex flex-col gap-2">
          <Button size="lg" className="w-full" onClick={goVerify}>
            본인인증하기
          </Button>
          <Button variant="ghost" className="w-full" onClick={() => setOpen(false)}>
            다음에
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
