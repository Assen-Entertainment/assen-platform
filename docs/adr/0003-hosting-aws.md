# ADR-0003: 호스팅/배포 — AWS Seoul (ap-northeast-2) + ECS Fargate

- 날짜: 2026-06-12
- 상태: Accepted
- 결정자: 대표 (Geon Yong Kim) — 결정 스프린트 OQ-10, ralplan 합의(grand-design-plan 긴장점 9)

## 맥락

호스팅/리전/배포 타겟은 hosting ADR로 위임된 미결 항목이었다. 한국 개인정보(휴대폰/이메일/
이름)의 리전 거주성, PG(PortOne/토스페이먼츠) 연동, Celery worker/beat 상주 프로세스,
에이전트의 프로덕션 무권한 원칙(#30)이 제약 조건이다.

## 결정

**AWS Seoul `ap-northeast-2` 리전을 전제로 설계·배포한다.**

- **런타임: ECS Fargate** — Django API / Celery worker / Celery beat를 각각 ECS 서비스로
  상주시킨다. 워커 상주형 구조라 scale-to-zero형(Cloud Run류)보다 운영 형태가 자연스럽다.
- **데이터:**
  - RDS PostgreSQL (Multi-AZ 여부는 트래픽 단계 보고 후 본 ADR 개정으로 결정)
  - ElastiCache Redis — Celery 브로커, rate limit, idempotency, opaque 토큰 캐시
  - S3 — private bucket + signed URL(이미지 업로드/조회, 접근 감사). §object storage adapter의 구현체
  - CloudFront — 정적 자산·이미지 CDN
- **배포 경로:** CI → ECR(컨테이너 레지스트리) → ECS, 앞단 ALB.
  프로덕션 배포 승인은 인간(#30) — 에이전트는 프로덕션 자격증명을 갖지 않는다.
- **시크릿:** AWS Secrets Manager. 로컬 `.env`는 에이전트 deny(#27) 유지.
- **PII 거주성:** 한국 PII는 Seoul 리전 내 보관, 리전 외 복제 금지.
- **PG:** 초기 PortOne 경유 검토, 토스페이먼츠 빌링(#10). 결제 트랙(ASS-83)은 승인 게이트
  보류 상태를 유지한다.

## 대안 검토

- **Cloud Run(GCP)**: scale-to-zero는 API에 유리하나 Celery worker/beat 상주와 어긋나고,
  관리 포인트가 GCP/AWS로 갈라진다. 채택 안 함.
- **Fly.io 등 경량 PaaS**: 초기 속도는 빠르나 한국 리전 데이터 거주성·관리형 PG·조직
  권한 분리(인간 게이트) 면에서 AWS 대비 열위. 채택 안 함.

## 결과

- dev 서버(= `dev` 브랜치 배포 대상)와 prod(= `main`)를 동일 토폴로지의 분리 환경으로
  구성한다(GitOps — AGENTS.md). 환경 구축 자체는 별도 인프라 작업으로 Linear에서 추적.
- docker-compose는 로컬/CI 개발용이며 프로덕션 토폴로지(ECS)와 서비스 구성을 일치시킨다
  (postgres/redis/api/celery-worker/celery-beat).
- 비용·Multi-AZ·오토스케일 파라미터는 트래픽 실측 후 본 ADR 개정으로 다룬다.
