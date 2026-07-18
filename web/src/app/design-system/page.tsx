import type { Metadata } from "next";
import Link from "next/link";

// 내부용 디자인시스템 인덱스 — 검색 노출 제외(noindex). 기존 루트(/) 미리보기를 이전.
export const metadata: Metadata = {
  title: "디자인 시스템",
  robots: { index: false, follow: false },
};

const LINKS = [
  { href: "/gallery", label: "DS 갤러리" },
  { href: "/discovery", label: "디스커버리" },
  { href: "/creator", label: "크리에이터 프로필" },
  { href: "/store", label: "스토어" },
  { href: "/checkout", label: "체크아웃" },
];

export default function DesignSystemIndex() {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-3 p-8">
      <h1 className="text-display-m text-on-surface">Assen</h1>
      <p className="text-body-m text-on-surface-variant">웹 디자인시스템 미리보기 (내부용)</p>
      <nav className="mt-4 flex flex-col gap-2">
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className="rounded-md border border-outline px-4 py-3 text-label text-on-surface transition-colors hover:bg-surface-container-high"
          >
            {l.label}
          </Link>
        ))}
      </nav>
    </main>
  );
}
