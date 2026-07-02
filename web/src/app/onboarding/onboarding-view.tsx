"use client";
import * as React from "react";
import Link from "next/link";
import { StepIndicator, Chip, Button } from "@/components/ui";
import { CheckIcon } from "@/lib/icons";
import { cn } from "@/lib/utils";
import { creatorAccentVars } from "@/lib/creator-accent";
import type { Creator } from "@/lib/api";

const INTERESTS = ["일러스트", "뮤직", "버튜버", "게임", "굿즈", "코스프레"];

export function OnboardingView({ creators }: { creators: Creator[] }) {
  const [step, setStep] = React.useState(0);
  const [interests, setInterests] = React.useState<string[]>([]);
  const [picked, setPicked] = React.useState<string[]>([]);
  const toggleI = (x: string) => setInterests((p) => (p.includes(x) ? p.filter((i) => i !== x) : [...p, x]));
  const toggleC = (id: string) => setPicked((p) => (p.includes(id) ? p.filter((i) => i !== id) : [...p, id]));

  return (
    <main className="min-h-screen bg-surface px-4 py-8">
      <div className="mx-auto flex max-w-2xl flex-col gap-6">
        <StepIndicator steps={["관심사", "크리에이터", "완료"]} current={step} className="self-center" />

        {step === 0 ? (
          <section className="flex flex-col gap-4">
            <h1 className="text-headline text-on-surface">어떤 콘텐츠를 좋아하세요?</h1>
            <p className="text-body-m text-on-surface-variant">관심사를 골라 맞춤 추천을 받아보세요.</p>
            <div className="flex flex-wrap gap-2">
              {INTERESTS.map((x) => (
                <Chip key={x} selected={interests.includes(x)} onClick={() => toggleI(x)}>
                  {x}
                </Chip>
              ))}
            </div>
            <Button size="lg" className="mt-4 self-end" disabled={interests.length === 0} onClick={() => setStep(1)}>
              다음
            </Button>
          </section>
        ) : null}

        {step === 1 ? (
          <section className="flex flex-col gap-4">
            <h1 className="text-headline text-on-surface">관심 크리에이터를 팔로우하세요</h1>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              {creators.map((c) => {
                const on = picked.includes(c.id);
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => toggleC(c.id)}
                    style={c.accentColor ? creatorAccentVars(c.accentColor) : undefined}
                    className={cn("flex flex-col gap-1.5 rounded-lg p-1.5 text-left transition-shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary", on && "ring-2 ring-primary")}
                  >
                    <div className="relative aspect-square w-full overflow-hidden rounded-md bg-creator-accent">
                      {on ? (
                        <span className="absolute right-1.5 top-1.5 flex size-6 items-center justify-center rounded-full bg-primary text-on-primary">
                          <CheckIcon className="size-4" />
                        </span>
                      ) : null}
                    </div>
                    <span className="line-clamp-1 text-label text-on-surface">{c.name}</span>
                    <span className="line-clamp-1 text-caption text-on-surface-variant">{c.category}</span>
                  </button>
                );
              })}
            </div>
            <div className="mt-4 flex justify-between">
              <Button variant="ghost" onClick={() => setStep(0)}>이전</Button>
              <Button size="lg" onClick={() => setStep(2)}>
                {picked.length ? `${picked.length}명 팔로우하고 시작` : "건너뛰기"}
              </Button>
            </div>
          </section>
        ) : null}

        {step === 2 ? (
          <section className="flex flex-col items-center gap-4 py-12 text-center">
            <div className="flex size-16 items-center justify-center rounded-full bg-primary-container text-on-primary-container">
              <CheckIcon className="size-8" />
            </div>
            <h1 className="text-headline text-on-surface">시작할 준비가 됐어요!</h1>
            <p className="text-body-m text-on-surface-variant">{picked.length}명의 크리에이터를 팔로우했어요.</p>
            <Button size="lg" asChild>
              <Link href="/discovery">홈으로</Link>
            </Button>
          </section>
        ) : null}
      </div>
    </main>
  );
}
