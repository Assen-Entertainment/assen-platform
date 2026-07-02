# PR

## 무엇을 / 왜

-

## 게이트 확인 (해당 항목만)

- [ ] server: `pytest` · `ruff` · `mypy` · `makemigrations --check` green
- [ ] web: `npm run build`(타입+ESLint) · `npm test` green
- [ ] Flutter: `melos format/analyze/test` green (Dart 변경 시)
- [ ] OpenAPI 계약: `server/scripts/export_openapi.py` + `npm run gen:types` 재생성 후 드리프트 없음 (API 변경 시)
- [ ] 신규 Django 모델: **migrations 미생성**(migration-less·run-syncdb 관례, server/AGENTS.md)

## 인간 게이트 (해당 시 체크 — 단독 머지 금지)

- [ ] 인증/세션/토큰 코드 (#26 인간 리뷰)
- [ ] 결제/정산/가격/약관/본인인증/IAP (대표·법무 게이트)
- [ ] DB `migrate`(로컬 초과) / 프로덕션 배포 (#25/#30)

## 참조

- Linear: ASS-
