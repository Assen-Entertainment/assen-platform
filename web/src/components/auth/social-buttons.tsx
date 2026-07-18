"use client";
import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * 소셜 로그인 버튼 — 각 provider의 **브랜드 가이드**(색상 + 로고)를 따른 표준 버튼.
 * 카카오(#FEE500·검정 말풍선), 네이버(#03C75A·흰 N), 구글(흰 배경·테두리·멀티컬러 G).
 * 브랜드 색은 라이트/다크 공통(브랜드 규정) — 테마 토큰을 쓰지 않는다.
 */
export type SocialProvider = "kakao" | "google" | "naver";

function KakaoIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden className="size-full">
      <path d="M12 3.6c-5.11 0-9.25 3.27-9.25 7.3 0 2.6 1.73 4.89 4.34 6.19-.19.7-.69 2.56-.79 2.96-.12.49.18.48.38.35.15-.1 2.42-1.64 3.4-2.31.63.09 1.27.14 1.92.14 5.11 0 9.25-3.27 9.25-7.29S17.11 3.6 12 3.6z" />
    </svg>
  );
}

function NaverIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden className="size-full">
      <path d="M14.2 12.4 9.5 5.5H5.4v13h4.4v-6.9l4.7 6.9h4.1v-13h-4.4v6.9z" />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden className="size-full">
      <path fill="#4285F4" d="M45.12 24.5c0-1.56-.14-3.06-.4-4.5H24v8.51h11.84c-.51 2.75-2.06 5.08-4.39 6.64v5.52h7.11c4.16-3.83 6.56-9.47 6.56-16.17z" />
      <path fill="#34A853" d="M24 46c5.94 0 10.92-1.97 14.56-5.33l-7.11-5.52c-1.97 1.32-4.49 2.1-7.45 2.1-5.73 0-10.58-3.87-12.31-9.07H4.34v5.7C7.96 41.07 15.4 46 24 46z" />
      <path fill="#FBBC05" d="M11.69 28.18C11.25 26.86 11 25.45 11 24s.25-2.86.69-4.18v-5.7H4.34C2.85 17.09 2 20.45 2 24s.85 6.91 2.34 9.88l7.35-5.7z" />
      <path fill="#EA4335" d="M24 10.75c3.23 0 6.13 1.11 8.41 3.29l6.31-6.31C34.91 4.18 29.93 2 24 2 15.4 2 7.96 6.93 4.34 14.12l7.35 5.7c1.73-5.2 6.58-9.07 12.31-9.07z" />
    </svg>
  );
}

const BUTTONS: {
  provider: SocialProvider;
  label: string;
  className: string;
  icon: React.ReactNode;
}[] = [
  {
    provider: "kakao",
    label: "카카오로 계속하기",
    className: "bg-[#FEE500] text-[rgba(0,0,0,0.85)] hover:bg-[#f2d900]",
    icon: <KakaoIcon />,
  },
  {
    provider: "naver",
    label: "네이버로 계속하기",
    className: "bg-[#03C75A] text-white hover:bg-[#02b350]",
    icon: <NaverIcon />,
  },
  {
    provider: "google",
    label: "Google로 계속하기",
    className:
      "border border-[#dadce0] bg-white text-[#3c4043] hover:bg-[#f8f9fa] dark:border-[#5f6368] dark:bg-[#131314] dark:text-[#e3e3e3] dark:hover:bg-[#1f1f1f]",
    icon: <GoogleIcon />,
  },
];

/** provider별 표준 브랜드 버튼 3종. ``onProvider``는 클릭 시 소셜 로그인 개시 콜백. */
export function SocialButtons({
  onProvider,
  disabled,
}: {
  onProvider: (provider: SocialProvider) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-col gap-2">
      {BUTTONS.map((b) => (
        <button
          key={b.provider}
          type="button"
          disabled={disabled}
          onClick={() => onProvider(b.provider)}
          className={cn(
            "relative flex h-12 w-full items-center justify-center rounded-lg text-label font-medium transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface",
            "disabled:pointer-events-none disabled:opacity-60",
            b.className,
          )}
        >
          <span aria-hidden className="absolute left-4 flex size-5 items-center justify-center">
            {b.icon}
          </span>
          {b.label}
        </button>
      ))}
    </div>
  );
}
