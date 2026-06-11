# Assen Platform

메이드카페 '하츠코이'의 오프라인 경험을 온라인으로 잇는 크로스플랫폼 서비스.
오프라인 방문(Fan CRM)을 기록·연결하는 것이 P0이며, 이후 Likey/Bubble류 온라인 활동(멤버십·메시지·디지털 체키)으로 확장한다.

- 프론트엔드: Flutter (web + iOS + Android) — web은 로그인 후 앱 경험 전용 (SEO 표면은 assen-landing)
- 백엔드: Django 5.2 LTS + Django Ninja (ADR-0001)
- 태스크 추적: Linear — 팀 ASS, 프로젝트 "Assen Platform"

## 문서

| 문서 | 내용 |
|---|---|
| `AGENTS.md` | 에이전트 하네스 (필수 선행 문서, 검증 계약, 금지 영역) |
| `docs/CONSTRAINTS.md` | 개발 제약사항 41개 (기준 문서) |
| `docs/adr/` | 아키텍처 결정 기록 |
| `docs/research/` | 제약의 근거 리서치 (하네스 담론, 스택·IAP·컴플라이언스) |

코드 scaffold는 아직 없다. scaffold 전에 `docs/CONSTRAINTS.md`와 Company-OS 거버넌스 문서를 읽을 것.
