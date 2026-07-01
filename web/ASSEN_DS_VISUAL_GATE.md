# Assen DS 시각 게이트 (WSL 전용)

빌드 → 스크린샷 → Figma 픽셀 비교. Windows 세션에서는 JS 빌드/dev 서버가 불가하므로 **WSL에서 수행**한다. 코드·토큰·Figma 정합과 브랜드 루브릭은 이미 통과(정적/프로그래매틱). 이 게이트는 **런타임 시각 회귀 확인**용.

## 1. 스캐폴드 + 실행
`ASSEN_WEB_SETUP.md` 절차대로 스캐폴드 후:
```bash
pnpm install
pnpm dev        # http://localhost:3000/gallery 확인
```

## 2. 스크린샷 (Playwright)
```bash
pnpm add -D playwright && npx playwright install chromium
node scripts/visual-gate.mjs
# → .screenshots/gallery-{light,dark,mobile}.png
# → .screenshots/screen-{discovery,creator,store,checkout}.png  (서비스 플로우)
```

## 3. Figma 기준 캡처
Figma MCP `get_screenshot`(파일 `Snd7m8KauF51QBZL5LWuGu`, 페이지 `5:3`)으로 동일 컴포넌트 캡처. 주요 노드:

| 컴포넌트 | Figma 노드 | 코드 |
|---|---|---|
| MonetizableItem | 256:28 | monetizable-item.tsx |
| CreatorThumbCard | 31:7 | creator-thumb-card.tsx |
| MembershipTierCard | 19:3 | membership-tier-card.tsx |
| EmptyState | 39:9 | empty-state.tsx |
| SearchField | 16:8 | search-field.tsx |
| Switch/Checkbox/Radio | 14:6 / 13:5 / 13:8 | switch·checkbox·radio.tsx |
| Divider/PriceLabel/Spinner/Skeleton | 12:9 / 51:10 / 50:7 / 52:8 | 각 파일 |
| Dialog/Menu/Tabs/Tooltip/Snackbar | 83:13 / 85:14 / 109:18 / 54:10 / 116:21 | dialog·dropdown-menu·tabs·tooltip·toast.tsx |
| AppBar/BottomNav/ListItem | 17:19 / 17:3 / 15:4 | appbar·bottom-nav·list-item.tsx |
| Avatar/Badge | 12:8 / 11:15 | avatar·badge.tsx |

(나머지는 `get_metadata`로 노드 매핑.)

## 4. 비교 + 수용 기준
코드 스크린샷 ↔ Figma 캡처 나란히: **색·간격·타이포·radius·elevation** 일치 확인. 차이는 아래 "의도적 편차"인지, **회귀**인지 구분 → 회귀면 수정 후 재촬영.

## 5. 알려진 의도적 편차 (브랜드 루브릭 상향 — 회귀 아님, Figma 상향 동기 권고)
- **CreatorThumbCard**: 이름 fs12→`title-m`, 회색 커버→`gradient.brand` 폴백 (C·B)
- **EmptyState**: 회색 서클→`primary-container` 틴트 (D)
- **MembershipTierCard**: `featured` 시 `gradient.brand` 상단 바 (B)
- **Switch**: off track `neutral-300`(=Figma #d4d4d8, 다크 `neutral-700` 대응), thumb 항상 white
- **Badge success/warning**: 중립 필→`success-container`/`warning-container` filled (a11y AA, 신규 토큰·Figma 동기 완료)
- **PriceLabel**: 원가(취소선)+할인%(error) 지원 추가

## 6. 체크리스트
- [ ] 라이트/다크 양모드 렌더 정상 (색 반전)
- [ ] creatorAccent 스코프 박스 대비 정상
- [ ] 오버레이(Dialog/Menu/Tooltip/Toast) 열림·포커스 트랩·스크림
- [ ] 폼 포커스 링(2px primary + offset) 일관
- [ ] 위 의도적 편차 외 Figma와 시각 일치
