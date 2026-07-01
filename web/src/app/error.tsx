"use client";
import { useEffect } from "react";
import { EmptyState, Button } from "@/components/ui";
import { ErrorIcon } from "@/lib/icons";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <main className="flex min-h-screen items-center justify-center bg-surface p-8">
      <EmptyState
        title="문제가 발생했어요"
        description="잠시 후 다시 시도해 주세요. 계속되면 문의해 주세요."
        icon={<ErrorIcon className="size-7" />}
        action={<Button onClick={reset}>다시 시도</Button>}
      />
    </main>
  );
}
