"use client";
import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { waGwa } from "@/lib/korean";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { MediaImage } from "@/components/ui/media-image";
import { VerifiedMark } from "@/components/ui/verified-mark";
import { ProgressBar } from "@/components/ui/progress-bar";
import { ConnectionGlow } from "@/components/ui/connection-glow";
import { AnimatedCount } from "@/components/ui/animated-count";
import { GiftIcon } from "@/lib/icons";

/**
 * CreatorHomeHeader — Figma DS(22:3). 크리에이터 프로필 above-the-fold 히어로(루브릭 #13).
 * 커버(실 사진 우선 · 폴백은 저채도 톤 표면 + 그레인, 크리에이터 액센트 조용히 틴트) + 아바타
 * 오버랩(화이트 링+그림자) + VerifiedMark 소비 + 팔로우 상태 전환 CTA(#18) + 통계 행.
 * 액센트 CSS 변수는 상위(creatorAccentVars) 스코프 필요.
 */
export interface CreatorHomeHeaderProps {
  name: string;
  handle: string;
  initial: string;
  /** 아바타 실 이미지 URL — 없으면 initial 폴백(Avatar 기존 동작). */
  avatarUrl?: string;
  /** 커버 실 이미지 URL — 없으면 저채도 톤 표면 폴백(seed=handle, 크리에이터 액센트 틴트). */
  coverUrl?: string;
  followers: number;
  posts?: number;
  verified?: boolean;
  bio?: string;
  /** 톤 폴백을 크리에이터 액센트로 틴트(false=기본 브랜드 틴트). */
  accent?: boolean;
  following?: boolean;
  followPending?: boolean;
  onToggleFollow?: () => void;
  onGift?: () => void;
  /** 뷰어가 이 프로필의 주인(본인)이면 팔로우·후원 컨트롤을 숨긴다(자기 팔로우/후원 방지). */
  isOwner?: boolean;
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
  avatarUrl,
  coverUrl,
  followers,
  posts,
  verified,
  bio,
  accent,
  following,
  followPending,
  onToggleFollow,
  onGift,
  isOwner,
  followersHref,
  goal,
  menu,
}: CreatorHomeHeaderProps) {
  // 연결 글로우(시그니처) — 팔로우가 실제로 성사되는 순간(following: false→true)에만 1회 재생하고
  // 조용한 확인 마이크로카피를 잠깐 띄운다. 언팔로우/초기 하이드레이션에는 발화하지 않는다.
  const [glow, setGlow] = React.useState(false);
  const [connected, setConnected] = React.useState(false);
  // 첫 렌더 시점의 값으로 초기화 → 이미 팔로잉 상태로 로드되면(하이드레이션) 발화하지 않는다.
  const prevFollowing = React.useRef(following);
  React.useEffect(() => {
    const was = prevFollowing.current;
    prevFollowing.current = following;
    // 팔로우 "성사"(비팔로우/미정[undefined|false] → 팔로우[true])에만 1회 발화.
    // 초기 already-following·언팔로우는 제외(was !== true 가드).
    if (following === true && was !== true) {
      setGlow(true);
      setConnected(true);
      const t = setTimeout(() => setConnected(false), 2600);
      return () => clearTimeout(t);
    }
    if (following !== true) setConnected(false);
  }, [following]);

  // 살아있는 숫자 — 팔로워 카운트가 tabular 틱업(±1). reduced-motion은 즉시 갱신(AnimatedCount).
  const followers_ = <AnimatedCount value={followers} className="text-on-surface" />;
  return (
    <header className="flex flex-col">
      {/* 커버 배너 — 실 커버 사진 우선, 없으면 프리미엄 톤 표면(저채도 + 그레인). 크리에이터 액센트로
          조용히 틴트(크리에이터 카드와 동일). 와이드 배너 + 아바타 오버랩이라 모노그램은 끈다(아바타가
          아이덴티티 마크). 예전의 채도 높은 워시·글로시 블룸/시트 모티프는 미니멀 럭셔리 방향에서 제거. */}
      <MediaImage
        src={coverUrl}
        alt={`${name}의 커버 이미지`}
        seed={handle}
        tintVar={accent ? "var(--creator-accent)" : undefined}
        monogram={false}
        className="h-44 w-full rounded-xl ring-1 ring-inset ring-on-surface/10 sm:h-56"
      />

      {/* 커버 아래 헤더(#5) — 아바타는 커버에 프로미넌트하게 오버랩하되, 이름·액션 버튼은
          커버에서 충분히 내려와 숨 쉬게 한다(커버와 밀착 방지·오버랩 리듬 정돈). */}
      <div className="px-2">
        <Avatar
          src={avatarUrl}
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
          <div className="relative flex shrink-0 gap-2">
            {/* 본인 프로필에서는 팔로우·후원을 숨긴다 — 자기 자신을 팔로우/후원할 수 없다. */}
            {onGift && !isOwner ? (
              <Button variant="outline" onClick={onGift} className="gap-1.5">
                <GiftIcon aria-hidden className="size-5" /> 후원
              </Button>
            ) : null}
            {!isOwner ? (
              /* 시그니처 모먼트 — 팔로우↔팔로잉 전환을 의도적으로: min-w 고정(토글 시 폭 점프/CLS 0),
                 팔로잉 상태엔 체크가 success-pop 으로 등장(reduced-motion 은 globals 전역 가드로 축소).
                 팔로우 성사 시 버튼 뒤로 크리에이터 액센트 "연결 글로우"가 번진다(브랜드 시그니처).
                 글로우는 z-0(버튼 뒤)·장식이라 버튼 라벨 대비를 건드리지 않는다. */
              <span className="relative inline-flex isolate">
                <ConnectionGlow show={glow} depth="follow" onDone={() => setGlow(false)} />
                <Button
                  variant={following ? "outline" : "accent"}
                  disabled={followPending}
                  aria-pressed={following}
                  onClick={onToggleFollow}
                  className="relative z-10 min-w-[5.5rem]"
                >
                  {following ? (
                    <>
                      <svg
                        viewBox="0 0 24 24"
                        aria-hidden
                        className="size-4 [animation:success-pop_260ms_ease-out]"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={3}
                      >
                        <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      팔로잉
                    </>
                  ) : (
                    "팔로우"
                  )}
                </Button>
              </span>
            ) : null}
            {menu}
            {/* 조용한 확인 — 액션 지점에서 잔잔히 뜨는 리추얼 마이크로카피(role=status로 낭독).
                absolute라 레이아웃을 밀지 않고(CLS 0), 오른쪽 정렬로 통계행 텍스트와 겹치지 않는다. */}
            {connected ? (
              <p
                role="status"
                className="pointer-events-none absolute right-0 top-full z-20 mt-2 whitespace-nowrap text-caption text-on-surface-variant [animation:overlay-in_320ms_ease-out]"
              >
                이제 <span className="font-medium text-on-surface">{name}</span>
                {waGwa(name)} 연결됐어요
              </p>
            ) : null}
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
