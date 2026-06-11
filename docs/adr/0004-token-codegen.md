# ADR-0004: 디자인 토큰 코드젠 도구

- 날짜: 2026-06-12
- 상태: **Proposed** — P1 스파이크(pass/fail 게이트) 결과로 확정한다
- 결정자: 대표 (Geon Yong Kim) — 결정 스프린트 OQ-11(단일 소스 확정), 도구 선택은 스파이크 종속

## 맥락

디자인 토큰의 단일 소스는 `docs/design/tokens.json`(DTCG 2025.10)이다. 소비자는 둘이다:
Flutter 앱(Dart ThemeExtension)과 Vite 공개 랜딩(CSS 변수). OQ-11 대표 결정으로
**양쪽 모두 동일 tokens.json에서 생성하며 드리프트를 수용하지 않는다.**
DTCG 도구체인(Style Dictionary의 DTCG 지원)은 미성숙 가능성이 있어 P1에서 timeboxed
스파이크로 검증한다.

## 결정 (Proposed)

- **시도:** Figma Variables → DTCG `tokens.json` → Style Dictionary →
  ① Dart 원시 토큰 + ThemeExtension(`packages/core_tokens`) ② Vite CSS 변수(`landing/src`).
- **fallback(사전 선언):** 스파이크 fail 시 수동 ThemeExtension으로 즉시 전환하되,
  tokens.json을 사람이 읽는 단일 기준으로 유지한다.
- **경계:** 수동 ColorScheme는 코드젠 대상이 아니다(#32 생성 파일 손편집 금지의 적용 밖).
  코드젠 산출물은 ref 색 램프·spacing·radius 등 원시 토큰에 한정한다.

## 수용 기준 (스파이크 pass 조건)

1. `melos run codegen`이 산출물을 손편집 0으로 재생성한다(#32).
2. 생성된 Vite CSS 변수가 기존 `landing/src/style.css` `:root` 값과 **diff 0**
   (시각 회귀 0 — 랜딩 빌드 green).
3. 토큰 1종에 대한 골든 테스트 1개 통과(베이스라인 인간 승인 #31).

## 결과

- pass 시: 본 ADR을 Accepted로 갱신하고 도구 버전을 고정 기록한다.
- fail 시: fallback 채택을 본 ADR에 기록하고, Figma Variables와의 동기화는 수동 절차
  (체크리스트)로 문서화한다.
- 추적: Linear ASS-128.
