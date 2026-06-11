---
title: AI 에이전트 하네스 담론 조사 (Karpathy 외)
date: 2026-06-11
status: 리서치
owner: Assen Entertainment
tags: [Research, LLM, Harness, Agent]
related:
  - "[[CONSTRAINTS]]"
  - "[[LLM_Harness_Index]]"
---

# AI 에이전트 개발의 하네스(Harness)와 제약 설계 — 담론 조사 (2024–2026)

조사일: 2026-06-11. 방법: 병렬 웹 리서치 + 1차 출처 fetch 검증. 검증 실패 인용은 UNVERIFIED 표기.
주의: "Karpathy가 'agents need a harness'라고 말했다"는 직접 인용은 검증 불가 — 실제 표현은 "leash(목줄)"와 "autonomy slider".

## 1. Andrej Karpathy

- **Vibe coding (2025.2)**: "코드의 존재 자체를 잊는" 코딩. 본인이 "throwaway weekend projects에는 나쁘지 않다"로 한정 — 저위험 프로토타입 전용. (simonwillison.net/2025/Mar/19/vibe-coding/)
- **진지한 코드 (2025.4)**: "이 과잉의욕 주니어 인턴 서번트에게 아주 짧은 목줄(tight leash)을 채워라… slow, defensive, careful, paranoid. 위임하지 말고 인라인 학습 기회를 잡아라." (x.com/karpathy/status/1915581920022585597)
- **YC 강연 "Software Is Changing (Again)" (2025.6)**: SW 1.0(코드)/2.0(가중치)/3.0(프롬프트=영어).
  - "Iron Man 로봇이 아니라 Iron Man 수트" — 완전 자율이 아닌 부분 자율 증강 + autonomy slider.
  - "AI를 목줄에 묶어둬야 한다. 너무 과활동적이다." / "큰 diff가 무섭다. 항상 작은 점진적 청크로, 루프를 매우 빠르게."
  - 에이전트를 위해 빌드: 문서를 마크다운으로, llms.txt 제공, "클릭하세요" 대신 실행 가능한 curl. (donnamagi.com/articles/karpathy-yc-talk)
- **Context engineering (2025.6)**: 컨텍스트 윈도우를 "딱 맞는 정보로 채우는 섬세한 기술". (simonwillison.net/2025/Jun/27/context-engineering/)
- **Dwarkesh 팟캐스트 (2025.10)**: "decade of agents". 에이전트 실패 모드: deprecated API 사용, 코드 비대화(bloating), 한 번도 쓰인 적 없는 novel 코드에 약함, "인터넷의 전형적 방식" 기억으로 코드를 오해. 잘 맞는 곳: boilerplate. (dwarkesh.com/p/andrej-karpathy)
- **nanochat (2025.10)**: "single, cohesive, minimal, readable, hackable, maximally-forkable… 거대 설정 객체, 모델 팩토리, if-then-else 괴물 없음." (github.com/karpathy/nanochat)
- **2026.1**: 한 달 만에 에이전트 사용 비중 80%로 전환 보고. 단 "미묘한 개념적 오류", "100줄이면 될 것을 1000줄로", 질문으로 명확화하지 않음 — "slopacolypse" 경고. (pixelsham.com/2026/01/27/andrej-karpathy-...)

## 2. Anthropic 공식

- **Building effective agents (2024.12)**: 가장 단순한 패턴부터. 워크플로 vs 에이전트 구분. "매 단계 환경에서 ground truth(도구 결과, 코드 실행)를 얻는 것이 결정적". 도구 설계(ACI)를 프롬프트만큼 진지하게(poka-yoke). 체크포인트 인간 피드백 + 최대 반복 정지 조건. (anthropic.com/engineering/building-effective-agents)
- **Claude Code best practices** (code.claude.com/docs/en/best-practices):
  - 검증 루프 1순위: "Claude가 직접 돌릴 수 있는 체크를 줘라. 그것이 '지켜봐야 하는 세션'과 '자리를 비울 수 있는 세션'의 차이." / "체크가 없으면 'looks done'이 유일한 신호이고, 당신이 검증 루프가 된다." / "검증할 수 없으면 배포하지 마라."
  - Explore → Plan → Code → Commit. 단 "diff를 한 문장으로 설명할 수 있으면 계획 생략."
  - CLAUDE.md: 넣을 것 = 추측 불가능한 명령, 기본값과 다른 규칙, 환경 quirk, 함정. 뺄 것 = "코드를 읽어서 알 수 있는 모든 것". "비대한 CLAUDE.md는 실제 지시를 무시하게 만든다." 매 줄 "지우면 실수하는가?" 테스트.
  - 같은 문제 2회 교정 → /clear 후 재시작이 거의 항상 우월.
  - 작성자≠검토자: fresh context 리뷰, 검증 서브에이전트가 결과를 반박. "성공을 주장하지 말고 증거를 보여라."
  - "CLAUDE.md는 권고, hook은 강제" — migrations 폴더 쓰기 차단 hook이 공식 예시.
- **Memory 문서**: 파일당 200줄 이하. 검증 가능한 구체 지시("2-space indentation"). "같은 실수 두 번째에 추가". (code.claude.com/docs/en/memory)
- **Effective context engineering (2025.9)**: 컨텍스트는 한계 자원("attention budget"). 시스템 프롬프트는 "적정 고도(right altitude)". 사전 로딩보다 just-in-time 검색 + progressive disclosure. 장기 작업엔 compaction + NOTES.md + 서브에이전트 요약. (anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- **Writing effective tools (2025.9)**: 원시 API 래핑 금지, 워크플로 단위 도구. 의미 있는 식별자. 모호성 없는 파라미터명. (anthropic.com/engineering/writing-tools-for-agents)
- **Boris Cherny**: "좋은 계획이 있으면 거의 매번 구현을 one-shot." 검증 프롬프트: "Grill me on these changes", "Prove to me this works". "모델 위의 가장 얇은 래퍼… 매 결정에서 가장 단순한 옵션". 모델이 좋아지면 하네스 코드 삭제. (newsletter.pragmaticengineer.com/p/building-claude-code-with-boris-cherny)

## 3. Simon Willison

- **Lethal trifecta (2025.6)**: ①사적 데이터 접근 + ②신뢰 불가 콘텐츠 노출 + ③외부 통신 — 결합 시 데이터 탈취. 해법은 한 다리 제거. 탐지형 가드레일 불신: "웹 보안에서 95%는 낙제점." (simonwillison.net/2025/Jun/16/the-lethal-trifecta/)
- **99%도 낙제** (CaMeL 리뷰): 확률적 탐지가 아닌 설계에 의한 보안. (simonwillison.net/2025/Apr/11/camel/)
- **Vibe coding 규율 (2025.3)**: "리뷰·테스트·이해하면 그건 vibe coding이 아니라 소프트웨어 개발이다." 골든룰: "남에게 정확히 설명할 수 없는 코드는 커밋하지 않는다."
- **Vibe engineering (2025.10)**: "견고하고 포괄적이고 안정적인 테스트 스위트가 있으면 에이전트 도구는 난다(fly)." (simonwillison.net/2025/Oct/7/vibe-engineering/)
- **외주 불가**: "기계에 절대 외주 줄 수 없는 한 가지는 코드가 실제로 작동하는지 테스트하는 것… 실행되는 걸 보지 않았다면 작동하는 시스템이 아니다."
- **YOLO 모드 (2025.9)**: 권한 생략은 컨테이너에서, 신뢰 호스트로 네트워크 잠그고, 한도 있는 테스트 크레덴셜만. (simonwillison.net/2025/Sep/30/designing-agentic-loops/)

## 4. OpenAI / Cognition(Devin) / Cursor / 기타

- **OpenAI practical guide**: 단일 에이전트 능력 극대화 먼저. 가드레일은 계층 방어. 도구를 읽기/쓰기·가역성·권한·금전 영향으로 위험 등급화. HITL 트리거 = 실패 임계 초과, 고위험·비가역 행동. (cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)
- **AGENTS.md 스펙**: "README for agents". 모노레포 중첩 + 가까운 파일 우선. Codex 32KiB/파일 제한. (agents.md)
- **Codex 샌드박스**: workspace-write + 네트워크 차단 기본, 경계 밖 승인 에스컬레이션. "샌드박스가 승인 피로를 줄인다."
- **Cognition/Devin**: "Don't Build Multi-Agents" — 전체 트레이스 공유, 단일 스레드. 3시간 룰(사람 3시간 = 에이전트 가능 단위), 명시적 완료 기준, 검증 쉬운 태스크. "최종 정확성의 책임은 당신에게." (cognition.ai/blog/dont-build-multi-agents)
- **Cursor rules**: 500줄 이하, glob 경로 스코핑, 중첩 지원. (cursor.com/docs/context/rules)
- **METR (2025.7)**: 숙련 OSS 개발자가 AI 도구로 19% 느려졌으나 20% 빨라졌다고 믿음 — 자기 인식이 아닌 측정·검증 규율의 근거. (metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/)

## 5. 하네스 정의와 에이전트 친화 코드베이스

- **LangChain**: "Agent = Model + Harness. 하네스는 모델이 아닌 모든 코드·설정·실행 로직." (langchain.com/blog/the-anatomy-of-an-agent-harness)
- **Böckeler (martinfowler.com/articles/harness-engineering.html)**: 하네스 = 피드포워드 '가이드'(규칙) + 피드백 '센서'(린터·타입체커·테스트) 둘 다. "피드백만 있으면 같은 실수를 반복하고, 피드포워드만 있으면 효과를 확인 못 한다."
- **Addy Osmani**: "괜찮은 모델 + 훌륭한 하네스 > 훌륭한 모델 + 나쁜 하네스." "좋은 AGENTS.md의 모든 줄은 실제로 잘못됐던 구체적 사건으로 거슬러 올라갈 수 있어야 한다." (addyosmani.com/blog/agent-harness-engineering/)
- **코드베이스 특성**: "AGENTS.md보다 코드베이스 자체가 AI 출력 품질의 최대 변수" — 깊은 모듈, 동작을 잠그는 테스트, 작은 집중 모듈, 개별 테스트 고속 실행, pre-commit 자동 감지. (aihero.dev, marmelab.com/blog/2026/01/21/agent-experience.html)
- **사고 사례 (docker.com/blog/ai-coding-agent-horror-stories-security-risks/)**: Replit 에이전트의 코드 프리즈 중 프로덕션 DB 삭제, Claude Code `rm -rf ~/`, AWS Kiro 프로덕션 삭제 13시간 장애, AI 커밋 시크릿 유출률 3.2%(베이스라인의 2배, GitGuardian). 결론: "비가역 작업의 확인 요구는 프롬프트 레이어가 아니라 플랫폼 레이어에. 자연어 지시는 보안 경계가 아니다. 인프라가 경계다."
- **OWASP LLM06 Excessive Agency**: 최소 권한 + 고영향 행동 human-in-the-loop.

## 핵심 교차 합의

1. 에이전트에게 기계 판정 가능한 검증 루프를 주되, 작성자가 채점하지 못하게 하라.
2. 규칙 파일은 짧게·사건 기반으로. 강제는 자연어가 아닌 인프라(hook/sandbox/CI)로.
3. 비가역 영역(마이그레이션·결제·인증·시크릿·프로덕션)은 권한 설계 차원에서 인간 게이트.

→ 적용 제약은 [[CONSTRAINTS]] 4장에 반영.
