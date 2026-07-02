import Link from "next/link";
import { EmptyState, Button } from "@/components/ui";
import { WarningIcon } from "@/lib/icons";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-surface p-8">
      <EmptyState
        title="페이지를 찾을 수 없어요"
        description="주소가 바뀌었거나 삭제된 페이지일 수 있어요."
        icon={<WarningIcon className="size-7" />}
        action={
          <Button asChild>
            <Link href="/">홈으로</Link>
          </Button>
        }
      />
    </main>
  );
}
