import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { VerifiedMark } from "@/components/ui/verified-mark";
import { ProgressBar } from "@/components/ui/progress-bar";
import { GiftIcon } from "@/lib/icons";

/**
 * CreatorHomeHeader — Figma DS(22:3). 크리에이터 프로필 above-the-fold 히어로(루브릭 #13).
 * 커버(creatorAccent 그라디언트) + 아바타 오버랩(화이트 링+그림자) + VerifiedMark 소비 +
 * 팔로우 상태 전환 CTA(#18) + 통계 행. 액센트 CSS 변수는 상위(creatorAccentVars) 스코프 필요.
 */
export interface CreatorHomeHeaderProps {
  name: string;
  handle: string;
  initial: string;
  followers: number;
  posts?: number;
  verified?: boolean;
  bio?: string;
  /** 커버를 크리에이터 액센트 그라디언트로(false=gradient.brand). */
  accent?: boolean;
  following?: boolean;
  followPending?: boolean;
  onToggleFollow?: () => void;
  onGift?: () => void;
  /** 팔로워 목록 링크 경로. */
  followersHref?: string;
  /** 목표 진행(ProgressBar 소비, 루브릭 #10) — placeholder 수치. */
  goal?: { label: string; value: number; max: number };
  /** 액션 행 끝에 배치할 더보기 메뉴 슬롯(차단 등) — 미지정 시 렌더 안 함. */
  menu?: React.ReactNode;
}

function compact(n: number): string {
  return n >= 1000 ? (n / 1000).toFixed(1).replace(/\.0$/, "") + "k" : String(n);
}

export function CreatorHomeHeader({
  name,
  handle,
  initial,
  followers,
  posts,
  verified,
  bio,
  accent,
  following,
  followPending,
  onToggleFollow,
  onGift,
  followersHref,
  goal,
  menu,
}: CreatorHomeHeaderProps) {
  const followers_ = (
    <span className="tabular-nums text-on-surface">{followers.toLocaleString("ko-KR")}</span>
  );
  return (
    <header className="flex flex-col">
      <div
        className="relative h-44 w-full overflow-hidden rounded-xl ring-1 ring-inset ring-white/10 sm:h-56"
        style={
          accent
            ? { backgroundImage: "linear-gradient(135deg, var(--creator-accent), var(--creator-accent-container))" }
            : { backgroundImage: "var(--gradient-brand)" }
        }
      >
        {/* 커버 광원·깊이 모티프(다층) — 크리에이터 색이 살아 있는 히어로.
            상단 화이트 블룸(광원) + 하단 다크 블룸(부피) + 대각 시트 하이라이트 + 하단 스크림. */}
        <div aria-hidden className="pointer-events-none absolute -right-12 -top-16 size-56 rounded-full bg-white/15 blur-2xl" />
        <div aria-hidden className="pointer-events-none absolute -bottom-16 -left-20 size-64 rounded-full bg-black/10 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute inset-0 bg-gradient-to-tr from-white/10 via-transparent to-transparent" />
        <div aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black/25 to-transparent" />
      </div>

      {/* 커버 아래 헤더(#5) — 아바타는 커버에 프로미넌트하게 오버랩하되, 이름·액션 버튼은
          커버에서 충분히 내려와 숨 쉬게 한다(커버와 밀착 방지·오버랩 리듬 정돈). */}
      <div className="px-2">
        <Avatar
          fallback={initial}
          size="xl"
          tone={handle}
          className="-mt-14 rounded-full shadow-2 ring-4 ring-surface sm:-mt-16"
        />
        <div className="mt-4 flex flex-wrap items-end justify-between gap-x-4 gap-y-3">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <h1 className="truncate text-headline text-on-surface sm:text-display-m">{name}</h1>
              {verified ? <VerifiedMark size="md" /> : null}
            </div>
            <p className="mt-0.5 text-body-s text-on-surface-variant">@{handle}</p>
          </div>
          <div className="flex shrink-0 gap-2">
            {onGift ? (
              <Button variant="outline" onClick={onGift} className="gap-1.5">
                <GiftIcon aria-hidden className="size-5" /> 후원
              </Button>
            ) : null}
            <Button
              variant={following ? "outline" : "accent"}
              disabled={followPending}
              aria-pressed={following}
              onClick={onToggleFollow}
            >
              {following ? "팔로잉" : "팔로우"}
            </Button>
            {menu}
          </div>
        </div>
      </div>

      {/* 통계 행 — 사회적 증거(팔로워·포스트). */}
      <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-1 px-2 text-body-s text-on-surface-variant">
        <div className="flex items-center gap-1">
          <dt className="sr-only">팔로워</dt>
          <dd>
            {followersHref ? (
              <Link href={followersHref} className="hover:text-on-surface hover:underline">
                팔로워 {followers_}
              </Link>
            ) : (
              <>팔로워 {followers_}</>
            )}
          </dd>
        </div>
        {posts ? (
          <div className="flex items-center gap-1">
            <dt className="sr-only">포스트</dt>
            <dd>
              포스트 <span className="tabular-nums text-on-surface">{posts.toLocaleString("ko-KR")}</span>
            </dd>
          </div>
        ) : null}
      </dl>

      {bio ? <p className="px-2 py-4 text-body-m text-on-surface">{bio}</p> : null}

      {goal ? (
        <div className={cn("mx-2 mt-2 rounded-lg border border-outline bg-surface-container p-3")}>
          <ProgressBar accent showValue label={goal.label} value={goal.value} max={goal.max} />
          <p className="mt-1 text-caption text-on-surface-variant">
            팔로워 {compact(goal.value)} / 목표 {compact(goal.max)} · ※ 데모 수치
          </p>
        </div>
      ) : null}
    </header>
  );
}
