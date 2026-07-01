# Assen 웹 클라이언트 — 셋업 가이드 (React + Next.js + Tailwind v4 + Radix)

> 스택 결정 = [[assen-web-stack]]. 빌드/설치/실행은 **WSL**(Flutter와 동일). 본 저장소엔 토큰·유틸·기본 컴포넌트가 이미 작성돼 있고(`src/**`, `scripts/`), 아래는 스캐폴드 + 배선 절차다. ⚠️ 작성물은 **WSL `pnpm dev` 전까지 미검증 초안**.

## 1. 스캐폴드 (WSL)
`web/` 에 이미 `src/styles`, `src/lib`, `src/components`, `scripts/` 가 있으므로, create-next-app 은 **임시 폴더에 생성 후 설정/app 파일만 병합**하는 게 안전하다.
```bash
cd assen-platform
pnpm create next-app@latest _webtmp --ts --eslint --app --src-dir --import-alias "@/*" --no-tailwind
# _webtmp 의 package.json·tsconfig.json·next.config.ts·src/app·public 등을 web/ 으로 복사(기존 src/* 보존)
rsync -a --ignore-existing _webtmp/ web/ && rm -rf _webtmp
cd web
```

## 2. 의존성
```bash
pnpm add clsx tailwind-merge class-variance-authority @radix-ui/react-slot
pnpm add @radix-ui/react-dialog @radix-ui/react-tabs @radix-ui/react-switch @radix-ui/react-checkbox @radix-ui/react-radio-group @radix-ui/react-dropdown-menu @radix-ui/react-tooltip @radix-ui/react-toast @radix-ui/react-slot @radix-ui/react-avatar
pnpm add -D tailwindcss @tailwindcss/postcss postcss
```

## 3. Tailwind v4 배선
**`postcss.config.mjs`**
```js
export default { plugins: { "@tailwindcss/postcss": {} } };
```
**`src/app/layout.tsx`** — 기본 `globals.css` 대신 우리 것 임포트(+ 다크 토글 대비 `className`):
```tsx
import "@/styles/globals.css";
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
```
(create-next-app 이 만든 `src/app/globals.css` 는 삭제 — 우리는 `src/styles/globals.css` 사용.)

## 4. 작성된 파일 (이미 존재)
| 파일 | 역할 |
|---|---|
| `src/styles/tokens.css` | 디자인 토큰 CSS변수(라이트 `:root`/다크 `.dark`) — tokens.v2.json 미러 |
| `src/styles/globals.css` | Tailwind v4 + `@theme`(색/radius/타이포/shadow) + 다크 variant + base |
| `src/lib/utils.ts` | `cn()` (clsx+tailwind-merge) |
| `src/lib/creator-accent.ts` | 런타임 크리에이터 액센트(WCAG 자동대비) → `creatorAccentVars()` |
| `src/components/ui/button.tsx` | Button(cva·Radix Slot, primary/secondary/outline/ghost/accent · sm/md/lg) |
| `src/components/ui/card.tsx` | Card / CardBody |
| `src/components/ui/monetizable-item.tsx` | MonetizableItem(type/title/price/meta, Figma 260:28 매핑) |
| `scripts/build-tokens.mjs` | tokens.v2.json → tokens.css 재생성 (`node scripts/build-tokens.mjs`) |

## 5. 데모 (`src/app/page.tsx` 로 붙여 검증)
```tsx
"use client";
import { useState } from "react";
import { MonetizableItem, type MonetizableItemType } from "@/components/ui/monetizable-item";
import { Button } from "@/components/ui/button";
import { creatorAccentVars } from "@/lib/creator-accent";

const ITEMS: { type: MonetizableItemType; title: string; price: string; meta: string }[] = [
  { type: "goods", title: "굿즈 상품명", price: "₩30,000", meta: "재고 12개 · 한정" },
  { type: "digital", title: "디지털 화보집", price: "₩5,000", meta: "다운로드 콘텐츠" },
  { type: "experience", title: "포토카드 팬사인", price: "₩12,000", meta: "11/30 20:00 · 선착순 30" },
  { type: "ticket", title: "라이브 입장권", price: "₩15,000", meta: "입장 1회 · 30일" },
  { type: "coupon", title: "10% 할인 쿠폰", price: "₩3,000", meta: "30일 유효" },
  { type: "membership", title: "베이직 멤버십", price: "₩9,900/월", meta: "월 구독 · 자동결제" },
];

export default function Page() {
  const [dark, setDark] = useState(false);
  return (
    <div className={dark ? "dark" : ""}>
      <main className="min-h-screen bg-surface p-8">
        <div className="mx-auto max-w-5xl">
          <div className="mb-6 flex items-center justify-between">
            <h1 className="text-display-m text-on-surface">스토어</h1>
            <Button variant="outline" size="md" onClick={() => setDark((d) => !d)}>
              {dark ? "라이트" : "다크"} 토글
            </Button>
          </div>
          {/* 런타임 크리에이터 액센트 데모: 스코프에 base 색 주입 → bg-creator-accent 추종 */}
          <div style={creatorAccentVars("#E14B8A")} className="mb-6 rounded-lg bg-creator-accent p-4 text-on-creator-accent">
            크리에이터 액센트 스코프 (Coral 예시 · 자동 대비)
          </div>
          <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4">
            {ITEMS.map((it) => (
              <MonetizableItem key={it.title} {...it} onAction={() => alert(it.title)} />
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
```

## 6. 검증
```bash
pnpm dev   # http://localhost:3000 — 카드 그리드·CTA·다크 토글·액센트 스코프 확인
pnpm build # 타입/빌드 통과 확인
```
- 폰트(Pretendard Variable)는 추후 `next/font/local` 또는 OFL 번들로 추가(모바일 setup_pretendard.sh 와 동일 패밀리). 미설치 시 Apple SD Gothic Neo/sans-serif 폴백.
- `text-title-m` 등은 `@theme` 의 `--text-*`(size+line-height+weight) 매핑이라 자동 적용. `text-on-surface`/`bg-primary` 등 색 유틸은 `@theme inline` var() → 라이트/다크/액센트 자동 추종.

## 7. 다음 컴포넌트 (Figma DS → React)
우선순위: TextField·Chip·Badge·Avatar·Tag · PostCard·CreatorThumbCard·MembershipTierCard · Dialog/Tabs/Switch(Radix) · AppBar/Sidebar(웹 셸). 전부 동일 패턴(토큰 유틸 + cva + Radix).
