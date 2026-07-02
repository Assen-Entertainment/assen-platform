# ADR-0004: 디자인 토큰 코드젠 도구

- 날짜: 2026-06-12
- 상태: **Accepted (부분 대체, 2026-07-02)** — 도구 선택(Style Dictionary)은 유효하나, **단일 소스는 `tokens.json`(v0.1) → `tokens.v2.json`으로 교체 예정**(SDLC 02 §5 G012 → E12/M1 이관). 웹(React) 타깃은 별도 인스턴스 `web/scripts/build-tokens.mjs`가 이미 v2를 소비 중. Dart/landing 파이프라인의 v2 이관 전까지 본 ADR의 tokens.json 서술은 과도기 현황이다.
- 결정자: 대표 (Geon Yong Kim) — 결정 스프린트 OQ-11(단일 소스 확정), 도구 선택은 스파이크 종속

## 맥락

디자인 토큰의 단일 소스는 `docs/design/tokens.json`(DTCG 2025.10)이다. 소비자는 둘이다:
Flutter 앱(Dart ThemeExtension)과 Vite 공개 랜딩(CSS 변수). OQ-11 대표 결정으로
**양쪽 모두 동일 tokens.json에서 생성하며 드리프트를 수용하지 않는다.**
DTCG 도구체인(Style Dictionary의 DTCG 지원)은 미성숙 가능성이 있어 P1에서 timeboxed
스파이크로 검증했다.

## 결정 (Accepted)

- **채택:** `docs/design/tokens.json`(DTCG) → **Style Dictionary** →
  ① Dart 원시 토큰 + ThemeExtension(`packages/core_tokens/lib/src/*.gen.dart`)
  ② Vite CSS 변수(`landing/src/tokens.generated.css`).
  코드젠 도구는 `tools/tokens/`(npm 프로젝트, Node 런타임)에 둔다.
- **도구·버전 고정:**
  - `style-dictionary` **5.4.4** (npm, `tools/tokens/package.json` + `package-lock.json`).
    DTCG는 `usesDtcg: true`로 활성 — `$type`/`$value` 파싱 + `{color.ref.*}` 별칭 해석 정상.
  - Node v24 / npm 11. 빌드: `dart run melos run codegen` → `npm --prefix tools/tokens run build`.
  - 손편집 0 검증: `dart run melos run codegen:verify` (재생성 후 `git diff --exit-code`
    + `node tools/tokens/verify-css.mjs` CSS 오라클).
- **경계 (준수):** 수동 ColorScheme는 코드젠 대상이 아니다(#32 적용 밖). M3 시드(`ColorScheme.fromSeed`)는
  크림 서피스를 왜곡하므로(tokens.md §3/§7), 코드젠은 ref 색 램프·spacing·radius·elevation·motion
  원시 토큰만 생성하고, 시맨틱 `AssenColorScheme`은 `packages/core_tokens/lib/src/color_scheme.dart`에
  **손으로** 작성한다(생성 헤더 없음 = 손편집 허용 명시). 생성 파일은
  `// GENERATED — DO NOT EDIT BY HAND (#32)` 헤더를 단다.

## 수용 기준 결과 (스파이크 판정)

1. **PASS** — `melos run codegen`이 Dart 6파일 + CSS 1파일을 손편집 0으로 재생성.
   `codegen:verify`가 재생성 후 `git diff` 비었음을 증명.
2. **CONDITIONAL PASS** — 생성된 Vite CSS 변수가 기존 `landing/src/style.css` `:root`의
   **디자인 토큰 부분집합(40변수)과 값·이름 diff 0** (`verify-css.mjs`), Vite 빌드 green.
   단, 스파이크가 드러낸 사실: **기존 style.css는 tokens.json의 깨끗한 투영이 아니었다.**
   세 가지 드리프트(아래 "발견")는 도구 문제가 아니라 원본 CSS의 잠재 불일치이며,
   비-토큰 랜딩 로컬(`--gutter`/폰트/`--shadow-*`)은 생성 대상 밖으로 분리해 :root에 유지.
   → 도구체인은 diff-0 능력을 증명했고, 시각 출력은 기존과 동일(0 회귀).
3. **PASS (인프라)** — alchemist 골든 인프라 1개 동작(`packages/ui_kit/test/token_swatch_golden_test.dart`):
   `testWidgets`가 생성 토큰을 Assen 테마 하에서 렌더(파이프라인 증명)하고 통과.
   픽셀 베이스라인 `goldenTest`는 `skip: '...(#31)'`로 선언 — 베이스라인 PNG는
   `flutter test --update-goldens`(인간 게이트, guard.py 차단)로 인간이 생성·승인해야 한다.

## 발견 (원본 드리프트 — 후속, 본 스파이크 범위 밖)

스파이크가 `style.css`와 `tokens.json` 사이에서 발견한 실제 불일치(억지 봉합하지 않고 기록):

1. **그림자 알파:** tokens.json `elevation.level1.color = #2B272414`(알파 0x14 ≈ 0.078)인데
   `--shadow-1`은 `rgba(43,39,36,0.08)`. 0.078 ≠ 0.08. CSS는 기존 값을 그대로 유지(0 회귀),
   Dart는 정확한 hex8(`0x142B2724`)을 생성. 후속에서 둘 중 하나로 정합 필요.
2. **`--peach-bgs` 누락:** tokens.json에 `peach.bgSubtle = #FFF2E9`가 있으나 :root에는 없다
   (다른 hue는 전부 `-bgs` 존재 — peach만 누락). 정규 생성기는 `--peach-bgs`를 추가하므로
   diff-0를 위해 CSS 측은 의도적으로 누락을 유지. Dart `RefColors.peachBgSubtle`은 정상 생성.
3. **폰트 패밀리 표기:** tokens.json `"Cafe24 Ssurround"`(공백) vs CSS `'Cafe24Ssurround'`
   (@font-face family명). `--font-*`은 비-토큰 랜딩 로컬로 분리.

## 결과

- pass 확정 → 본 ADR Accepted. 위 발견은 별도 후속(랜딩 토큰 정합 또는 tokens.json 보정)으로
  처리하며, tokens.json은 단일 기준으로 유지된다.
- Figma Variables와의 동기화(역방향)는 P1 범위 밖 — Figma→tokens.json 내보내기는 추후 ADR.
- 추적: Linear ASS-128.
