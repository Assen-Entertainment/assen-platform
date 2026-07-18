import type { Metadata } from "next";
import Link from "next/link";
import { EmptyState, Button } from "@/components/ui";
import { WarningIcon } from "@/lib/icons";

export const metadata: Metadata = {
  title: "세션 만료",
  description: "로그인 세션이 만료되었습니다. 다시 로그인해 주세요.",
};

/** Session Expired — Figma Web-SessionExpired(196:377) / W3. 재로그인 CTA. */
export default function SessionExpiredPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-surface p-8">
      <EmptyState
        icon={<WarningIcon className="size-7" />}
        title="세션이 만료되었어요"
        description="보안을 위해 일정 시간 후 자동으로 로그아웃돼요. 다시 로그인해 이어서 이용해 주세요."
        action={
          <div className="flex gap-2">
            <Button asChild>
              <Link href="/login">다시 로그인</Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/discovery">둘러보기</Link>
            </Button>
          </div>
        }
      />
    </main>
  );
}
