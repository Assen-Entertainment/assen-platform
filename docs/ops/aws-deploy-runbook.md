# AWS 배포 런북 — 웹 MVP (all-AWS) (2026-07-13)

> 대상: 웹 MVP 소프트런치(`docs/ops/mvp-release-boundary-2026-07-13.md`). **배포 = 전부 AWS** 확정.
> - **API(Django/daphne)** = ECS Fargate (`infra/terraform`, `scripts/deploy-prod-ecs.sh`).
> - **웹(Next.js)** = **AWS Amplify Hosting**(관리형 SSR·CDN·SSL). terraform엔 웹이 없으므로 Amplify로 분리(모두 AWS).
> - region = `ap-northeast-2`(서울, ADR-0003).
> - AWS 리소스 생성 명령은 **계정 소유자(건용)** 가 실행. region은 모든 명령에서 `ap-northeast-2`.
>
> ⚠️ **첫 배포는 staging(`config.settings.demo`, mock ON)으로 "인프라+부팅+서빙"만 검증**한 뒤, prod 설정 + 실 provider를 순차 연결한다(Phase 7). 실 결제/본인인증/OTP/스토리지 없이도 스택이 뜨는지 먼저 확인.

---

## Phase 0 — 계정 · CLI · 비용 (지금)
1. **root 사용 금지** → IAM 관리자 사용자 생성(또는 IAM Identity Center). 액세스 키 발급.
   ```sh
   aws configure            # Access Key / Secret / region=ap-northeast-2 / json
   aws sts get-caller-identity   # 자격 확인
   ```
2. **비용 알림**: Billing → Budgets에서 월 예산 + 알림(예: $150) 설정. (소형 스택도 RDS/Redis/ALB로 월 $60~150.)

**완료 기준**: `aws sts get-caller-identity`가 내 계정을 반환.

---

## Phase 1 — terraform 상태 백엔드 + 네트워크
1. **tfstate 백엔드**(S3 버킷 + DynamoDB 락):
   ```sh
   ACCT=$(aws sts get-caller-identity --query Account --output text)
   aws s3api create-bucket --bucket assen-tfstate-$ACCT --region ap-northeast-2 \
     --create-bucket-configuration LocationConstraint=ap-northeast-2
   aws s3api put-bucket-versioning --bucket assen-tfstate-$ACCT \
     --versioning-configuration Status=Enabled
   aws dynamodb create-table --table-name assen-tf-lock \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST --region ap-northeast-2
   ```
2. **네트워크(VPC)**:
   - **첫 staging(최속)**: 기본 VPC의 퍼블릭 서브넷 2개를 그대로 사용(태스크에 퍼블릭 IP 부여). 서브넷 id 조회:
     ```sh
     aws ec2 describe-subnets --filters Name=default-for-az,Values=true \
       --query 'Subnets[].SubnetId' --output text
     aws ec2 describe-vpcs --filters Name=isDefault,Values=true \
       --query 'Vpcs[0].VpcId' --output text
     ```
   - **prod 하드닝(후행)**: 전용 VPC + 퍼블릭(ALB)·프라이빗(Fargate/RDS) 서브넷 2AZ + NAT.

**완료 기준**: tfstate 버킷·락테이블 생성, VPC/서브넷 id 확보.

---

## Phase 2 — 데이터 · 시크릿 · 도메인
1. **RDS PostgreSQL 16**(프라이빗 권장; staging은 기본 VPC 가능):
   ```sh
   aws rds create-db-instance --db-instance-identifier assen-db \
     --engine postgres --engine-version 16 --db-instance-class db.t4g.micro \
     --allocated-storage 20 --db-name assen \
     --master-username assen --master-user-password '<STRONG_PW>' \
     --vpc-security-group-ids <db-sg> --no-publicly-accessible --region ap-northeast-2
   ```
   → 엔드포인트로 `DATABASE_URL=postgres://assen:<PW>@<endpoint>:5432/assen`.
2. **ElastiCache Redis 7**:
   ```sh
   aws elasticache create-cache-cluster --cache-cluster-id assen-redis \
     --engine redis --engine-version 7.1 --cache-node-type cache.t4g.micro \
     --num-cache-nodes 1 --security-group-ids <redis-sg> --region ap-northeast-2
   ```
   → `REDIS_URL=redis://<endpoint>:6379/0`.
3. **Secrets Manager**(값 저장, terraform은 ARN만 참조):
   ```sh
   python -c "import secrets;print(secrets.token_urlsafe(64))"   # SECRET_KEY 생성
   python -c "import secrets;print(secrets.token_hex(32))"       # PHONE_IDENTIFIER_HMAC_KEY 생성
   aws secretsmanager create-secret --name assen/secret-key      --secret-string '<SECRET_KEY>'      --region ap-northeast-2
   aws secretsmanager create-secret --name assen/database-url    --secret-string '<DATABASE_URL>'    --region ap-northeast-2
   aws secretsmanager create-secret --name assen/redis-url       --secret-string '<REDIS_URL>'       --region ap-northeast-2
   aws secretsmanager create-secret --name assen/phone-hmac-key  --secret-string '<PHONE_HMAC_KEY>'  --region ap-northeast-2
   ```
   → 각 ARN을 `prod.tfvars`의 `container_secrets`에 기입.
4. **ACM 인증서**(ALB HTTPS; `api.assenent.com`):
   ```sh
   aws acm request-certificate --domain-name api.assenent.com \
     --validation-method DNS --region ap-northeast-2
   ```
   → 출력된 CNAME을 DNS(Cafe24/Route53)에 추가해 검증 완료 → 인증서 ARN 확보.

**완료 기준**: `DATABASE_URL`·`REDIS_URL`·`SECRET_KEY`·`PHONE_HMAC` 시크릿 ARN 4개 + ACM ARN.

---

## Phase 3 — API 이미지(ECR) 준비
1. ECR repo는 terraform이 만든다(`create_ecr_repository=true`) → **먼저 Phase 4 apply로 repo만 생성 후** push하거나, 수동 생성:
   ```sh
   aws ecr create-repository --repository-name assen-platform-api --region ap-northeast-2
   ```
2. 이미지 빌드·push는 **Phase 5의 `deploy-prod-ecs.sh`** 가 자동 수행(ECR 로그인→`build-prod-image.sh`→`:{commit}`·`:prod` push). 수동 확인만 필요하면:
   ```sh
   aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin <acct>.dkr.ecr.ap-northeast-2.amazonaws.com
   ```

**완료 기준**: ECR repo URL 확보(`<acct>.dkr.ecr.ap-northeast-2.amazonaws.com/assen-platform-api`).

---

## Phase 4 — terraform apply (API 인프라)
1. `prod.tfvars` 작성(git-ignored):
   ```sh
   cd infra/terraform && cp example.tfvars prod.tfvars   # 값 채우기
   ```
   채울 값: `vpc_id`·`public_subnet_ids`·`private_subnet_ids`(staging은 public=private로 같게 가능)·`image_repository_url` 또는 `create_ecr_repository`·`acm_certificate_arn`·`container_secrets`(Phase 2 ARN)·`container_environment`:
   ```hcl
   container_environment = {
     DJANGO_SETTINGS_MODULE = "config.settings.prod"   # ← staging 검증 단계에선 "config.settings.demo"
     ALLOWED_HOSTS          = "api.assenent.com"
     DJANGO_ALLOWED_ORIGINS = "https://assenent.com"   # 웹 오리진(CORS)
   }
   ```
2. init → plan → apply:
   ```sh
   terraform init \
     -backend-config="bucket=assen-tfstate-<acct>" \
     -backend-config="key=prod/ecs.tfstate" \
     -backend-config="region=ap-northeast-2" \
     -backend-config="dynamodb_table=assen-tf-lock"
   terraform plan  -var-file=prod.tfvars
   terraform apply -var-file=prod.tfvars
   ```
3. **outputs → 배포 env 매핑**(README 표): `ecr_repository_url`·`ecs_cluster_name`·`ecs_api_service_name`·`ecs_worker_service_name`·`ecs_beat_service_name`·`ecs_migrate_taskdef_family`·`alb_dns_name`.

**완료 기준**: ECS 클러스터·서비스·ALB·migrate 태스크데프 생성, `terraform output` 값 확보.

---

## Phase 5 — 첫 배포(이미지 빌드+마이그레이션+롤링)
`deploy-prod-ecs.sh`가 전부 수행(ECR 빌드/push → migrate 태스크 실행·검증 → api/worker/beat 강제 롤링 → 안정화 대기 → `/healthz`·`/api/health` 스모크). terraform output을 env로:
```sh
export ASSEN_PROD_DEPLOY_APPROVED=1
export AWS_REGION=ap-northeast-2
export ASSEN_ECR_REPOSITORY_URI=$(terraform -chdir=infra/terraform output -raw ecr_repository_url)
export ASSEN_ECS_CLUSTER=$(terraform -chdir=infra/terraform output -raw ecs_cluster_name)
export ASSEN_ECS_API_SERVICE=$(terraform -chdir=infra/terraform output -raw ecs_api_service_name)
export ASSEN_ECS_WORKER_SERVICE=$(terraform -chdir=infra/terraform output -raw ecs_worker_service_name)
export ASSEN_ECS_BEAT_SERVICE=$(terraform -chdir=infra/terraform output -raw ecs_beat_service_name)
export ASSEN_ECS_MIGRATE_TASKDEF=$(terraform -chdir=infra/terraform output -raw ecs_migrate_taskdef_family)
export ASSEN_PROD_API_URL=https://api.assenent.com
# migrate 태스크에 네트워크 지정 필요(프라이빗 서브넷+SG):
export ASSEN_ECS_MIGRATE_NETWORK='awsvpcConfiguration={subnets=[subnet-...],securityGroups=[sg-...],assignPublicIp=ENABLED}'
sh scripts/deploy-prod-ecs.sh
```
- 스크립트는 **main 브랜치 + 클린 워크트리 + CI green** 을 요구(`ASSEN_ALLOW_NON_MAIN_PROD_DEPLOY=1`·`ASSEN_SKIP_GITHUB_CI_CHECK=1` 로 우회 가능하나 첫 검증 후 권장 안 함).
4. **도메인 → ALB**: DNS(Cafe24/Route53)에 `api.assenent.com` → `alb_dns_name`(CNAME/ALIAS).

**완료 기준**: `curl https://api.assenent.com/api/health` 200(commit·version 반환).

---

## Phase 6 — 웹(Next.js) = AWS Amplify Hosting
1. Amplify 콘솔 → **Host web app** → GitHub `Assen-Entertainment/assen-platform` 연결, 브랜치 `main`, **앱 루트 `web/`**.
2. **환경변수**: `NEXT_PUBLIC_API_URL=https://api.assenent.com` (★빌드타임에 이미지에 각인 — Amplify 빌드 설정에 반드시 지정).
3. 빌드 설정(Next.js 자동 감지) 확인 → 배포. Amplify가 SSR 컴퓨트·CDN·SSL 관리.
4. **도메인**: Amplify Domain management → `assenent.com`(또는 `app.assenent.com`) 연결(SSL 자동).
5. **CORS/쿠키**: API의 `DJANGO_ALLOWED_ORIGINS`에 웹 오리진 포함 확인. 웹↔API가 다른 서브도메인이면 httpOnly 쿠키는 `assenent.com` 공통 상위도메인 + `SameSite=None;Secure`.

**완료 기준**: `https://assenent.com` 로딩 + 로그인/디스커버리 정상(단, Phase 7 전엔 결제/가입은 mock/게이트 상태).

---

## Phase 7 — 앱 활성화 (mock → 실 provider, 순차)
prod에선 mock 전부 OFF라 아래가 fail-closed. **staging(demo)로 스택 검증 후** 하나씩 실 연결:
1. **가입 OTP**(`ENABLE_MOCK_FAN_OTP`): 실 SMS 발송 provider(또는 포트원 본인인증으로 통합) → `config/otp.py` 어댑터.
2. **결제**(`ENABLE_MOCK_PAYMENT`): 포트원 어댑터 + **결제 async 라이프사이클(PENDING→웹훅→PAID)** + 체크아웃 재배선(`PaymentGateway(ABC)` 시임에 연결).
3. **19+ 본인인증**(`ENABLE_MOCK_KYC`+`ENABLE_ADULT_CONTENT`): 포트원 본인인증 어댑터(`IdentityVerifier(ABC)` 시임) + `ENABLE_ADULT_CONTENT` ON + 법무.
4. **디지털 스토리지**(`SERVE_LOCAL_MEDIA`): **S3 + CloudFront** 구축 + `config/storage.py` 어댑터(현 미배선 gap).
5. **activation 블로커 점검**(production-readiness 감사): entrypoint dev fallback·mock 번들 잔존·OpenAPI 드리프트 등.

각 provider 심사(PG·본인인증·SMS)·통신판매업 신고·법무는 **병렬 외부 진행**.

---

## 부록
- **필수 시크릿**: `SECRET_KEY`·`DATABASE_URL`·`REDIS_URL`·`PHONE_IDENTIFIER_HMAC_KEY` (+ 후행: PG키·본인인증키·SMS키·S3 자격).
- **롤백**: `deploy-prod-ecs.sh`는 mutable `:prod` 태그를 롤. 이전 커밋 태그로 서비스 `update-service --force-new-deployment` 하거나 이전 태스크데프 리비전으로 롤백.
- **staging 최소경로**: Phase 1~5를 기본 VPC + `DJANGO_SETTINGS_MODULE=config.settings.demo`(mock ON)로 1회 → 스택/부팅/서빙 확인 → prod 전환.
- 관련: `docs/deployment.md` · `docs/adr/0003-hosting-aws.md` · `infra/terraform/README.md` · `docs/ops/mvp-release-boundary-2026-07-13.md`.
