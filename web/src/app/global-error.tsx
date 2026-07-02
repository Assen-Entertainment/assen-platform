"use client";
import "@/styles/globals.css";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="ko">
      <body>
        <main className="flex min-h-screen items-center justify-center bg-surface p-8 text-on-surface">
          <div className="flex flex-col items-center gap-3 text-center">
            <h1 className="text-headline">문제가 발생했어요</h1>
            <p className="text-body-m text-on-surface-variant">앱을 다시 불러와 주세요.</p>
            <button onClick={reset} className="rounded-md bg-primary px-4 py-2 text-label text-on-primary">
              다시 시도
            </button>
          </div>
        </main>
      </body>
    </html>
  );
}
