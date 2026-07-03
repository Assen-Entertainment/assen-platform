import type { Metadata } from "next";
import Link from "next/link";
import { EmptyState, Button } from "@/components/ui";

export const metadata: Metadata = {
  title: "접근 권한 없음",
  description: "이 페이지에 접근할 권한이 없습니다.",
};

/** 403 Forbidden — Figma Web-403(208:533) / W3. 권한 없음 + 홈 CTA. */
export default function ForbiddenPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-surface p-8">
      <EmptyState
        icon={<span aria-hidden className="text-2xl font-bold">403</span>}
        title="접근 권한이 없어요"
        description="이 페이지를 볼 수 있는 권한이 없어요. 계정이 올바른지 확인하거나 홈으로 돌아가 주세요."
        action={
          <div className="flex gap-2">
            <Button asChild>
              <Link href="/discovery">홈으로</Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/login">다른 계정으로 로그인</Link>
            </Button>
          </div>
        }
      />
    </main>
  );
}
