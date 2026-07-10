import * as React from "react";
import { Logo } from "@/components/ui/logo";

/**
 * AuthShell — 인증 화면(로그인·회원가입·비밀번호 재설정) 공통 브랜드 프론트도어.
 *
 * [브랜드 시그니처] 밋밋한 회색 카드 대신, warm-paper 캔버스 위에 gradient.brand(인디고→바이올렛)
 *  소프트 블룸을 깔고 상단에 Assen 로크업을 세운 뒤, 프로스티드 카드가 그 위로 부상한다.
 *  색 아이덴티티는 인디고 계열로 고정(발전형 폴리시 가드레일) — 블룸은 전부 --gradient-brand/primary 파생.
 *  블룸은 정적(모션 아님)이라 reduced-motion 무관하고, 로크업/카드만 fade-up 진입(전역 가드로 축소).
 *
 * 로크업은 페이지 최상위 <h1>(접근성 이름 "Assen") — 카드 내부 제목은 <h2>로 위계를 잇는다.
 */
export function AuthShell({
  children,
  subtitle = "크리에이터의 세계관을 팬과 잇는 무대",
}: {
  children: React.ReactNode;
  /** 로크업 하단 한 줄 카피. null이면 생략. */
  subtitle?: React.ReactNode;
}) {
  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-canvas p-4">
      {/* 브랜드 앰비언트 — indigo→violet 블룸(가드레일: gradient.brand/primary 파생). 순수 장식(aria-hidden). */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div
          className="absolute left-1/2 top-[-16%] size-[42rem] max-w-[130vw] -translate-x-1/2 rounded-full opacity-[0.14] blur-3xl"
          style={{ backgroundImage: "var(--gradient-brand)" }}
        />
        <div className="absolute -left-24 bottom-[-14%] size-[26rem] rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute -right-24 top-1/3 size-[22rem] rounded-full bg-primary/[0.07] blur-3xl" />
      </div>

      <div className="relative flex w-full max-w-sm flex-col items-center gap-6">
        {/* 브랜드 로크업 — 프론트도어 시그니처. h1 = 페이지 대표 제목("Assen"). */}
        <h1 className="flex flex-col items-center gap-2 text-center [animation:fade-up_500ms_ease-out]">
          <Logo size="lg" />
          {subtitle ? (
            <span className="text-body-s font-normal text-on-surface-variant">{subtitle}</span>
          ) : null}
        </h1>

        {/* 프로스티드 카드 — 브랜드 광원 위로 부상(hairline + shadow-2 + backdrop-blur). */}
        <div className="flex w-full flex-col gap-4 rounded-xl border border-outline/70 bg-surface/90 p-6 shadow-2 backdrop-blur-md [animation:fade-up_500ms_ease-out]">
          {children}
        </div>
      </div>
    </main>
  );
}
