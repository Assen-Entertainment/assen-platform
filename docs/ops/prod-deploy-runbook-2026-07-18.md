# 프로덕션 배포 런북 (2026-07-18)

**대상**: `assen-platform` 프로덕션 최초 기동 + 이후 릴리즈 루프
**범위**: E10 게이트(AWS 프로비저닝) 이후 사람이 그대로 따라 실행할 수 있는 절차
**정본 근거**: `.github/workflows/deploy.yml`, `scripts/deploy-prod-ecs.sh`,
`scripts/build-prod-image.sh`, `infra/terraform/*`, `server/config/settings/prod.py`,
`server/config/email.py`, `server/apps/uploads/**`, `AGENTS.md` §GitOps

> **갱신 이력**: 이 문서의 **오전 작성본은 낡았다**. 그 뒤로 6개 웨이브가 들어와
> 배포 파이프라인·terraform·이메일·업로드가 전부 바뀌었다. 이 판(오후)은 전 항목을
> **현재 코드에 재대조**해서 다시 썼다. 오전본이 "대표 판단 필요"라고 적었던
> B1(업로드)·B2(이메일)·B3(web 미배포)는 **오늘 코드로 닫혔다** — §0 참조.

> ⚠️ 이 문서를 쓴 시점에 **terraform은 한 번도 apply된 적이 없다**
> (`infra/terraform/README.md` §STATUS). `validate`는 통과하지만 실제 apply는
> 계정별 세부사항(쿼터·IAM 경계·정확한 secret ARN)을 새로 드러낸다.
> 아래에서 **확실하지 않은 항목은 "미검증"으로 명시**했다. 추측으로 채우지 않았다.

---

## 0. 오늘 닫은 것 / 아직 사람이 해야 하는 것

이 절만 읽어도 "무엇이 코드로 끝났고 무엇이 사람 손에 남았는지"가 보이게 쓴다.

### 0-1. ✅ 오늘 코드로 닫힌 것 (오전본의 블로커들)

| 오전본 | 무엇이었나 | 지금 |
|---|---|---|
| **B1 업로드 전면 503** | `SERVE_LOCAL_MEDIA` 하드코딩 False가 유일 게이트라 S3를 붙여도 무조건 503 | **해소.** `SERVE_LOCAL_MEDIA`는 **폐지**됐고(`base.py:446` 주석에 폐지 사유만 남음), 업로드 스위치는 **`ALLOW_UPLOADS` 하나**(env, 기본 False)다(`base.py:450`). `ALLOW_UPLOADS=true` + 버킷이면 **업로드가 실제로 열린다**. |
| **B2 이메일 가입 503** | 실 SES/SMTP 어댑터가 없어 `email_sender()`가 항상 None | **코드는 해소.** `SesEmailSender`(boto3 **SESv2** `send_email`) + `SmtpEmailSender` 존재(`config/email.py:193,146`). 다만 **SES 검증·샌드박스 탈출은 사람 작업** → §0-2. |
| **B3 web이 배포 파이프라인 밖** | `deploy.yml`/스크립트가 api·worker·beat만 굴림, web은 수동 | **해소.** `build-prod-image.sh:34-40`이 web 이미지를 빌드하고, `deploy-prod-ecs.sh:81-82`가 푸시, `:132`가 web 서비스까지 롤한다. **수동 web 빌드 절차는 삭제됐다.** |
| **R1 main 전용 가드 역전** | ref≠main이면 오히려 가드가 풀려 dev를 prod로 배포 가능 | **해소.** `deploy.yml:59` `ASSEN_ALLOW_NON_MAIN_PROD_DEPLOY: ""` → ref=main이면 진행, **ref≠main이면 `deploy-prod-ecs.sh:21-24`가 큰 소리로 실패**한다. |
| **R2 `image_tag`가 롤백처럼 보임** | 설명이 "roll to"였지만 실제로는 새 빌드 태그 | **해소(설명만).** `deploy.yml:17-22`가 "롤백이 아니다 / 현재 체크아웃을 그 태그로 다시 빌드한다"로 정정됐다. **동작은 그대로** — 롤백은 §6뿐. |
| **R3 ECR lifecycle이 prod 이미지 만료** | `tagStatus: any` + `imageCountMoreThan: 20` | **해소(코드상).** `ecr.tf:59-75`가 **untagged만 14일 후 만료**로 재작성 — `:prod`는 어떤 룰에도 매칭되지 않아 만료 불가. ⚠️ 단 실계정 적용은 §0-2 참조. |

### 0-2. ⛔ 아직 사람이 해야 하는 것 (코드로 못 뚫음)

| 항목 | 성격 | 없으면 프로덕션에서 |
|---|---|---|
| **실 PG 결제** | 가맹 계약 (대표) | 유료 체크아웃 **503 `PaymentsUnavailable`** — **소프트런치 스코프상 정상** |
| **실 19+ 본인인증** | provider 계약 + 법무 | 본인인증 503, adult_only 콘텐츠 전원 숨김 |
| **SES 아이덴티티 + DKIM/SPF DNS 검증** | AWS 계정 + DNS | 이메일 가입 **503** (코드는 준비됨) |
| **SES 샌드박스 탈출** | **AWS 지원 요청 — 리드타임 있음** | 사전 검증된 수신자에게만 메일 → **실제 팬 가입이 조용히 실패**. 반드시 탈출 후 오픈. |
| **법무 사인오프** (약관/개인정보/청소년보호) | 법무 | 페이지 미확정 |
| **자동 콘텐츠 모더레이션** | 대표·법무 게이트 | 없음 — 오늘의 posture는 **신고 기반 사람 테이크다운**(승인됨, §7) |
| **ECR lifecycle 실적용** | 계정 작업 (**비용만 — 배포 블로커 아님**) | `ecr.tf`의 정책은 **실 리포에 닿지 않는다**(양 tfvars가 `create_ecr_repository = false`). **2026-07-17 조회 결과 두 리포 모두 정책 없음** → **프로덕션 이미지 만료 위험 없음**, 남는 것은 **무한 스토리지 증가**뿐 (§7 R3). |
| **프로덕션 도메인 확정** | 대표 | ACM/ALLOWED_HOSTS/WEB_BASE_URL 전부 미확정 |

### 0-3. ✅ **`/media/*` ALB 누수 — 코드로 닫힘** (단, apply 후 육안 확인 필수)

**이 런북 작성 중 발견 → 같은 날 수정됨.** 경위와 남은 확인 절차를 함께 남긴다.

**무엇이었나.** 오늘부터 미디어는 **모든 백엔드에서 Django의 게이트된 뷰**가 서빙한다
(`config/urls.py:75` → `apps/uploads/media.py:84`, 경로 `/media/...`). 그런데 ALB 리스너
규칙은 API로 보내는 경로를 3개(`/api/*`, `/healthz`, `/readyz`)만 열거했고,
`deploy_web = true`면 default action은 **web 타깃 그룹**(`alb.tf:40`)이다 → 브라우저의
`https://<prod>/media/uploads/<uuid>.png`가 **Next로 가서 404**. Next에는 `/media` 라우트가
없다. `Upload.url`은 영속되고 Post/Product `media_url`로 복사되므로 **신규가 아니라 전 이미지가
동시에** 깨지는 결함이었다.

**무엇을 고쳤나 — 두 레이어다** (하나만 고치면 반쪽이다. 위상이 다르다):

| 레이어 | 수정 | 누가 타나 |
|---|---|---|
| **ALB** (prod) | `web.tf`의 `path_pattern.values`에 **`"/media/*"` 추가** | `브라우저 → 단일 ALB 오리진 → 리스너 규칙 → Django`. prod에서 Next는 이 요청을 **아예 보지 않는다** |
| **Next rewrite** (로컬·CI) | `web/next.config.mjs`에 `/media/:path*` → `API_PROXY_TARGET` rewrite 추가 | `브라우저 → Next(:3000) → rewrite → Django`. **ALB가 없는** 환경의 같은 hop |

> ⚠️ **두 번째 레이어는 별도 결함이었다** — 런북 초판은 ALB만 지적했으나, 로컬/CI에서도
> `/media`가 Next에 rewrite되지 않아 **개발 환경 이미지도 전부 404**였다. 눈에 띄지 않은 이유:
> `MediaImage`(`web/src/components/ui/media-image.tsx:37`)의 `onError` 폴백이 조용히 그라디언트
> 플레이스홀더로 되돌린다 — **깨진 이미지가 의도된 디자인처럼 렌더된다.**

**e2e도 함께 강화**: `web/e2e/studio-upload.spec.ts`가 `media_url` **문자열만** 단언하던 것이
이 결함이 숨은 직접 원인이었다. 이제 그 URL을 **실제로 GET해 200 + `image/*` + 비어있지 않은
바디**를 단언한다. **단 그 테스트는 ALB를 증명하지 않는다** — CI엔 ALB가 없다(아래 확인 절차 필수).

**⛔ 여전히 사람이 확인해야 하는 것 — apply 후 리스너 규칙 육안 확인.**
terraform 코드가 맞다는 것과 **실제 리스너에 규칙이 붙었다는 것은 다른 사실**이고, 이것이 틀리면
**모든 이미지가 조용히 깨진다**(위 폴백 때문에 "이미지가 없는 디자인"으로 보인다). §3-5 참조.

---

## 1. 전제 (E10 게이트)

`deploy.yml`이 **한 번이라도 성공하려면** 아래가 전부 참이어야 한다.
하나라도 없으면 `scripts/deploy-prod-ecs.sh`가 `: "${VAR:?}"`로 즉시 fail-closed 한다.

### 1-1. AWS 계정 측

| 항목 | 확인 방법 | 근거 |
|---|---|---|
| VPC + 퍼블릭 서브넷 2AZ(ALB용) + 프라이빗 서브넷 2AZ(태스크용) | `aws ec2 describe-subnets --filters Name=vpc-id,Values=<vpc>` | `alb.tf:6`, `ecs.tf:146` |
| **프라이빗 서브넷의 아웃바운드 경로**(NAT GW 또는 VPC 엔드포인트) | 라우트 테이블에 `0.0.0.0/0 → nat-…` 존재 확인 | `prod.tfvars: assign_public_ip=false`. **없으면 ECR pull 실패 → 서비스가 영원히 stabilize 안 됨** |
| RDS(PostgreSQL) 기동 + 태스크 SG에서 5432 접근 가능 | `aws rds describe-db-instances` | `iam.tf` 주석: RDS/ElastiCache는 terraform이 만들지 않음 |
| ElastiCache(Redis) 기동 | `aws elasticache describe-cache-clusters` | `prod.py:57-70`이 redis 강제 |
| ECR `assen-platform-api` 리포 | `aws ecr describe-repositories --repository-names assen-platform-api` | `ecr.tf:4-13` |
| ECR `assen-platform-web` 리포 | 위와 동일 (`assen-platform-web`) | `ecr.tf:18-27`. **terraform은 `create_ecr_repository && deploy_web`일 때만 만든다** — `prod.tfvars`는 `create_ecr_repository=false`이므로 **수동 생성 필요** |
| ACM 인증서 (**ap-northeast-2 리전**, 프로덕션 도메인 커버) | `aws acm list-certificates --region ap-northeast-2` → `Status=ISSUED` | `alb.tf:29-36`. ALB는 리전 리소스 → us-east-1 인증서 불가 |
| Route53 (또는 외부 DNS) 존 | — | §3-6 |
| Secrets Manager 항목 (§2 표의 `secret_arn_*` 전부) | `aws secretsmanager list-secrets` | `iam.tf:24-31` |
| **S3 미디어 버킷** — 생성 or 참조 (§1-4) | `aws s3api get-public-access-block --bucket <b>` | `media.tf`, `iam.tf:54-75`, `base.py:516` |
| **SES 검증 아이덴티티 + DKIM + 샌드박스 탈출** (§1-5) | `aws ses get-identity-verification-attributes --identities <domain>` | `iam.tf:94-109`, `config/email.py:193` |
| **GitHub OIDC provider** (`token.actions.githubusercontent.com`) | `aws iam list-open-id-connect-providers` | `deploy.yml:44-48` |
| **배포 IAM 역할** + trust policy | 아래 1-2 | `deploy.yml:47` |

> **미검증**: 위 목록은 코드가 요구하는 것에서 역산했다. 실제 apply가
> 추가 요구사항(서비스 쿼터, IAM 경계)을 드러낼 수 있다.

### 1-2. 배포 IAM 역할 (OIDC)

`deploy.yml`은 static key를 쓰지 않는다. `secrets.AWS_ROLE_TO_ASSUME` 역할이 필요하다.

**Trust policy** — `sub` 조건을 **반드시 `environment:production`으로 좁힐 것**
(`deploy.yml`은 `workflow_dispatch`라 임의 브랜치에서 디스패치될 수 있다. 스크립트가
main을 강제하긴 하지만, IAM은 그 앞단에서 좁혀 두는 것이 옳다):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:sub": "repo:Assen-Entertainment/assen-platform:environment:production"
      }
    }
  }]
}
```

**권한** — 스크립트가 실제로 호출하는 것만:
`ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`, `ecr:PutImage`,
`ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`,
`ecr:BatchGetImage`(`deploy-prod-ecs.sh:66-82` — **api·web 두 리포 모두**),
`ecs:RunTask`, `ecs:DescribeTasks`, `ecs:UpdateService`, `ecs:DescribeServices`
(`:88-146`), 그리고 migrate 태스크 롤 전달용 `iam:PassRole`(execution/task 역할 대상).

### 1-3. GitHub 측

| 항목 | 확인 방법 |
|---|---|
| **Environment `production` 생성 + Required reviewers 지정** | Settings → Environments → production. **이것이 유일한 인간 승인 게이트다** (`deploy.yml:40,52` — 스크립트의 `ASSEN_PROD_DEPLOY_APPROVED=1`은 워크플로가 무조건 넣어주므로, Environment 승인이 없으면 승인 게이트가 **아예 없다**) |
| **Deployment branches = `main` 한정** | 가드가 고쳐졌어도(§0-1 R1) GitHub 레벨에서 한 번 더 막는 것이 옳다 |
| §2-4의 secret / variable 전부 등록 | Environment 스코프 권장 (repo 스코프면 프로덕션 값이 모든 워크플로에 노출) |

> **필수 검토자 지명**: 대표(리포 admin). 실제 GitHub 계정명은 이 리포에서 확인
> 불가 → **미검증**, 대표가 직접 지정할 것.

### 1-4. S3 미디어 버킷 — 만들 것인가 참조할 것인가

**두 변수는 서로 다른 질문이다. 헷갈리면 반드시 사고가 난다.**

| 변수 | 질문 | 효과 |
|---|---|---|
| `create_media_bucket` (`variables.tf:195-199`, 기본 **false**) | **이 스택이 버킷을 만드나?** | true → `media.tf`의 리소스 생성. false → 아무것도 안 만듦 |
| `media_s3_bucket` (`variables.tf:189-193`, 기본 `""`) | **어떤 버킷을 쓰나?** | 비어있지 않으면 **태스크 롤에 S3 권한 부여**(`iam.tf:54-75`) |

둘이 분리된 이유: **dev는 이미 out-of-band로 만든 버킷을 참조**한다. 합쳐 버리면
dev apply가 남의 버킷을 만들려 들거나 IAM 권한을 잃는다.

- **그린필드 prod**: `create_media_bucket = true` + `media_s3_bucket = "<이름>"`
  → `media.tf`가 BPA 4종 all-true(`:32-39`), BucketOwnerEnforced(`:44-51`),
  SSE-S3(`:59-69`), 버저닝 on(`:86-93`), **MPU-abort 라이프사이클만**(`:107-123`),
  TLS-only 버킷 정책(`:150-158`)으로 만든다.
- **기존 버킷 참조**: `create_media_bucket = false` + `media_s3_bucket = "<이름>"`
  → **BPA 4종이 전부 true인지 직접 확인할 것.** terraform이 강제해 주지 않는다:
  ```sh
  aws s3api get-public-access-block --bucket <bucket> --region ap-northeast-2
  # BlockPublicAcls / IgnorePublicAcls / BlockPublicPolicy / RestrictPublicBuckets 전부 true
  ```

> **버킷은 프라이빗으로 유지할 것.** 오늘부터 브라우저는 버킷을 직접 읽지 않는다 —
> 앱 티어가 유일한 독자다(`base.py:501-515`, `apps/uploads/media.py`).

### 1-5. SES — 실 메일의 사람 전제

`config/email.py`의 어댑터는 준비돼 있다. 아래는 **전부 AWS 계정/DNS 작업**이다.

1. **아이덴티티 검증**: 도메인(권장) 또는 주소.
   **`EMAIL_SES_REGION`과 같은 리전**이어야 한다 — SES는 리전 서비스다.
2. **DKIM + SPF DNS 레코드** 등록 → `Verification status: Success` 확인.
3. **샌드박스 탈출**(AWS 지원 요청, **리드타임 있음**). 탈출 전에는
   **사전 검증된 수신자에게만** 메일이 간다 → 실제 팬 가입이 **조용히 실패**한다.
4. **`ses_identity_arn`** (`variables.tf:201-205`)을 tfvars에 설정
   → `iam.tf:94-109`가 태스크 롤에 **`ses:SendEmail`만**, **그 아이덴티티로 스코프**해서 부여.
   비워 두면 정책이 아예 생성되지 않는다.
5. **`EMAIL_FROM_ADDRESS`는 그 아이덴티티에 속해야 한다** — 아니면 SES 거부 + IAM 거부로 두 번 막힌다.

> **static AWS 키는 없다.** `SesEmailSender`는 boto3가 **ECS 태스크 롤**로 서명한다
> (`config/email.py:180-190` — 자격증명을 절대 넘기지 않음). SES-over-SMTP를 고르지 않은
> 이유가 이것이다(`iam.tf:77-88`).

---

## 2. 채워야 할 값

### 2-1. `infra/terraform/prod.tfvars` 플레이스홀더

> `prod.tfvars`는 **git-ignored**다 (`infra/terraform/.gitignore`: `*.tfvars` +
> `!example.tfvars`). **리포에 추적되는 tfvars는 `example.tfvars` 하나뿐**이고,
> `prod.tfvars`는 apply하는 머신에만 존재한다 → 이 표를 보고 재작성해야 한다.
>
> ⚠️ **오늘 아침에 쓰인 로컬 `prod.tfvars`에 낡은 줄이 남아 있다**: `~89`가
> "`SERVE_LOCAL_MEDIA`가 `base.py:393`에 하드코딩 False라 업로드 엔드포인트는 prod에서
> 503으로 남는다"고 주장한다. **셋 다 틀렸다** — 그 플래그는 폐지됐고, `base.py:393`은
> 그 내용이 아니며, 업로드는 `ALLOW_UPLOADS=true` + 버킷이면 열린다.
> **그 파일을 들고 있는 사람이 직접 고쳐야 한다**(리포에서 고칠 수 없다).

| 플레이스홀더 | 무엇 | 어디서 얻나 |
|---|---|---|
| `REPLACE_ME__prod_vpc_id` | 프로덕션 VPC id | `aws ec2 describe-vpcs` |
| `REPLACE_ME__prod_public_subnet_az_a` / `_c` | ALB용 퍼블릭 서브넷 2개 (서로 다른 AZ) | `aws ec2 describe-subnets` |
| `REPLACE_ME__prod_private_subnet_az_a` / `_c` | Fargate 태스크용 프라이빗 서브넷 2개 | 위와 동일. **NAT/엔드포인트 경로 필수** |
| `REPLACE_ME__aws_account_id` (api/web 2곳) | 12자리 AWS 계정 id | `aws sts get-caller-identity --query Account` |
| `REPLACE_ME__acm_cert_arn_ap_northeast_2` | ACM 인증서 ARN | `aws acm list-certificates --region ap-northeast-2` |
| `REPLACE_ME__prod_api_host` | 프로덕션 API/서비스 호스트 (예: `assen.co.kr`). 스킴 없이 | 대표 도메인 확정 — **미확정** |
| `REPLACE_ME__prod_web_origin` | 웹 오리진 (스킴 포함해 `https://…`로 조립됨) | 위와 동일. same-origin이면 api_host와 같은 값 |
| `REPLACE_ME__prod_redis_endpoint` (**5곳** — celery/ratelimit/channels가 DB 0/1/2를 나눠 씀) | ElastiCache 엔드포인트 호스트 | `aws elasticache describe-cache-clusters --show-cache-node-info` |
| `REPLACE_ME__prod_media_bucket` (**2곳** — `container_environment.DJANGO_MEDIA_S3_BUCKET` + `media_s3_bucket`) | 프라이빗 S3 미디어 버킷명. **두 곳이 같은 이름이어야 한다** (§2-3) | 생성 후 이름 |
| `ses_identity_arn` | SES 검증 아이덴티티 ARN | `arn:aws:ses:ap-northeast-2:<acct>:identity/<도메인>` |
| `REPLACE_ME__secret_arn_django_secret_key` | Django SECRET_KEY 시크릿 ARN | 아래 2-2 |
| `REPLACE_ME__secret_arn_database_url` | `postgres://user:pass@host:5432/db` 시크릿 ARN | 아래 2-2 |
| `REPLACE_ME__secret_arn_phone_hmac_key` | ≥32바이트 HMAC 키 시크릿 ARN (`prod.py:46-48`이 부팅 시 검사) | 아래 2-2 |
| `REPLACE_ME__secret_arn_{kakao,google,naver}_client_{id,secret}` | 소셜 OAuth 앱 자격증명 ARN | 각 개발자 콘솔에서 앱 등록. **미등록이면 그 줄을 지울 것** → 해당 provider 503 |
| `REPLACE_ME__secret_arn_sentry_dsn` | Sentry DSN (**선택**) | 안 쓰면 그 줄 삭제 |

**ARN은 AWS가 붙이는 6자 접미사까지 전부** 넣어야 한다
(`dev.tfvars` 예: `…:secret:assen/dev/django-secret-key-TDoY2O`).

### 2-2. Secrets Manager 항목 생성

```sh
# SECRET_KEY (>=50자, dev 키 재사용 절대 금지)
aws secretsmanager create-secret --name assen/prod/django-secret-key \
  --secret-string "$(python -c 'import secrets;print(secrets.token_urlsafe(64))')" \
  --region ap-northeast-2

# PHONE_IDENTIFIER_HMAC_KEY (>=32바이트 — prod.py:46-48이 부팅 시 거부)
aws secretsmanager create-secret --name assen/prod/phone-hmac-key \
  --secret-string "$(python -c 'import secrets;print(secrets.token_urlsafe(48))')" \
  --region ap-northeast-2

# DATABASE_URL
aws secretsmanager create-secret --name assen/prod/database-url \
  --secret-string "postgres://<user>:<pass>@<rds-endpoint>:5432/<db>" \
  --region ap-northeast-2
```

생성 후 각 ARN(`--query ARN`)을 `prod.tfvars`의 `container_secrets`에 붙여넣는다.

> **SES/S3용 시크릿은 없다.** 둘 다 태스크 롤로 서명한다 — 넣을 키가 없는 것이 정상이다.

### 2-3. 컨테이너 env — **오늘 새로 필요해진 7개**

`container_environment`(비밀 아님)에 들어간다. 전부 `example.tfvars`에 예시 있음.

| env | 값 | 근거 / 함정 |
|---|---|---|
| `EMAIL_SENDER_BACKEND` | `ses` (또는 `smtp`) | `base.py:67`. **모르는 값이면 prod가 부팅 실패**(`prod.py:79-84`) — 오타가 영원한 503으로 숨지 않게 한 의도적 설계. 비워 두면 조용히 503(정상). |
| `EMAIL_FROM_ADDRESS` | `no-reply@<도메인>` | `base.py:68`. **`ses_identity_arn`의 아이덴티티에 속해야 함** |
| `EMAIL_SES_REGION` | `ap-northeast-2` | `base.py:74`. **아이덴티티가 검증된 리전과 같아야 함** |
| `WEB_BASE_URL` | `https://<웹 오리진>` | `base.py:69`. **웹 오리진이지 API 호스트가 아니다** — `{WEB_BASE_URL}/verify-email?token=` 링크를 만든다(`config/email.py:103-110`). 틀리면 메일 링크가 404. |
| `ALLOW_UPLOADS` | `True` | `base.py:450`. **업로드의 유일한 스위치.** 기본 False(fail-closed). ⚠️ **§0-3 해결 전에는 켜지 말 것** |
| `DJANGO_MEDIA_S3_BUCKET` | 버킷명 | `base.py:516`. **이것이 백엔드를 실제로 켠다** |
| `DJANGO_MEDIA_S3_REGION` | `ap-northeast-2` | `base.py:522` |

**반쪽 배선(half-wire) — 둘 다 조용히 틀린다:**

| 증상 | 원인 | 결과 |
|---|---|---|
| grant는 있는데 백엔드가 없음 | `media_s3_bucket` 설정 + `DJANGO_MEDIA_S3_BUCKET` **미설정** | 앱이 **로컬 디스크**에 쓴다 → 태스크 재시작마다 이미지 소실 |
| 백엔드는 있는데 grant가 없음 | `DJANGO_MEDIA_S3_BUCKET` 설정 + `media_s3_bucket` **미설정** | **모든 업로드가 500 AccessDenied** |
| 업로드 503 | `ALLOW_UPLOADS` 미설정 | **설계된 정상 동작** |
| 업로드 503 (플래그는 켰는데) | S3 백엔드인데 버킷명이 빔 | `media_storage_ready()` False (`config/storage.py:42-69`) |

> **`SERVE_LOCAL_MEDIA`는 존재하지 않는다.** 폐지됐다(`base.py:446-449`). 어떤 env에도,
> 어떤 tfvars에도 넣지 말 것. 미디어는 **모든 백엔드에서 Django가 서빙**한다.

### 2-4. GitHub Environment `production` — secret / variable 전량

`terraform output` → GitHub Settings → Environments → `production`.
**근거**: `deploy.yml:44-73`, `deploy-prod-ecs.sh:30-37,88,100`

| GitHub 키 | 종류 | terraform output | 신규? |
|---|---|---|---|
| `AWS_ROLE_TO_ASSUME` | **secret** | *(없음 — §1-2에서 수동 생성한 역할 ARN)* | |
| `AWS_REGION` | variable (선택, 미설정 시 `ap-northeast-2`) | `var.aws_region` | |
| `ASSEN_ECR_REPOSITORY_URI` | variable | `ecr_repository_url` | |
| **`ASSEN_WEB_ECR_REPOSITORY_URI`** | variable | **`web_ecr_repository_url`** | ⭐ **신규** |
| `ASSEN_ECS_CLUSTER` | variable | `ecs_cluster_name` | |
| `ASSEN_ECS_API_SERVICE` | variable | `ecs_api_service_name` | |
| `ASSEN_ECS_WORKER_SERVICE` | variable | `ecs_worker_service_name` | |
| `ASSEN_ECS_BEAT_SERVICE` | variable | `ecs_beat_service_name` | |
| **`ASSEN_ECS_WEB_SERVICE`** | variable | **`ecs_web_service_name`** | ⭐ **신규** |
| `ASSEN_PROD_API_URL` | variable | `alb_dns_name`을 가리키는 **DNS 호스트** (`https://<prod-domain>`) | |
| `ASSEN_ECS_MIGRATE_TASKDEF` | variable | `ecs_migrate_taskdef_family` | |
| `ASSEN_ECS_MIGRATE_NETWORK` | variable | ⚠️ **대응 output 없음 — 아래 참조** | |

> 신규 2개가 **비면 배포가 시작조차 못 한다** — `deploy-prod-ecs.sh:31,36`이
> `: "${VAR:?}"`로 즉시 죽는다. 이것이 의도된 fail-closed다.

**`ASSEN_PROD_SITE_URL` — 워크플로에서 설정할 수 없다**

`deploy-prod-ecs.sh:43`이 읽지만 **`deploy.yml`이 넘겨주지 않는다**. 따라서 Actions
경로에서는 **항상 `ASSEN_PROD_API_URL`로 기본값**이 잡힌다:

```sh
WEB_SITE_URL="${ASSEN_PROD_SITE_URL:-${ASSEN_PROD_API_URL%/}}"
```

이 값은 **web 번들에 빌드타임으로 구워진다**(`NEXT_PUBLIC_SITE_URL`,
`build-prod-image.sh:37`). web과 api가 **같은 ALB 오리진을 공유하는 동안에만 맞다** —
현재 구조가 그렇다(`web.tf:67-82`). 오리진이 갈라지면 `deploy.yml`에 이 변수를
추가하는 **코드 변경**이 필요하다. (빈 값이면 `build-prod-image.sh:19`가 빌드를 실패시킨다.)

**`ASSEN_ECS_MIGRATE_NETWORK` — 유일하게 output이 없는 값**

`outputs.tf`에 서브넷/보안그룹 output이 없어서 손으로 조립해야 한다:

```
awsvpcConfiguration={subnets=[subnet-aaa,subnet-bbb],securityGroups=[sg-ccc],assignPublicIp=DISABLED}
```

- `subnets` = `prod.tfvars`의 `private_subnet_ids`
- `securityGroups` = terraform이 만든 `assen-prod-service` SG id — **output이 없으므로** apply 후 조회:
  ```sh
  aws ec2 describe-security-groups --filters Name=group-name,Values=assen-prod-service \
    --query 'SecurityGroups[0].GroupId' --output text --region ap-northeast-2
  ```
- `assignPublicIp=DISABLED` (`assign_public_ip=false`와 일치해야 함)

> **두 값 모두 사실상 필수다.** `ASSEN_ECS_MIGRATE_TASKDEF`가 비면 스크립트가
> migrate를 **건너뛰고**(`:126-129`) 테이블 없는 DB 위로 API를 배포한다.
> `ASSEN_ECS_MIGRATE_NETWORK`가 비면 `--network-configuration` 없이 awsvpc
> run-task를 호출해 태스크 배치가 실패하고 `:104-107`에서 배포가 중단된다.

---

## 3. 순서 (최초 프로비저닝)

### 3-1. terraform init

```sh
cd infra/terraform
terraform init \
  -backend-config="bucket=<tfstate-bucket>" \
  -backend-config="key=prod/ecs.tfstate" \
  -backend-config="region=ap-northeast-2" \
  -backend-config="dynamodb_table=<lock-table>"
```

state 버킷/락 테이블은 terraform이 만들지 않는다(닭-달걀). 없으면 먼저 수동 생성.

> 참고: terraform 1.15에서 `dynamodb_table`은 deprecated 경고를 낸다
> (`use_lockfile` 권장). 경고일 뿐 동작한다.

### 3-2. plan

```sh
terraform plan -var-file=prod.tfvars -out=prod.tfplan
```

**plan 결과에서 반드시 눈으로 확인**:
- `aws_ecr_repository.api` / `.web`가 **생성 대상이 아닐 것** (`create_ecr_repository=false`).
  생성 대상으로 뜨면 이미 존재하는 계정-전역 리포와 충돌한다.
- `aws_lb_listener.https`가 **생성될 것** (ACM ARN이 비면 안 뜬다 → 프로덕션이 HTTP로 뜬다).
- `aws_ecs_service.web`이 생성될 것 (`deploy_web=true`).
- `aws_s3_bucket.media`가 **의도대로일 것**: 그린필드면 생성, 기존 버킷 참조면
  **생성 대상이 아님**(`create_media_bucket=false`). 참조인데 생성으로 뜨면 §1-4를 다시 읽을 것.
- `aws_iam_role_policy.task_ses_send`가 생성될 것 (`ses_identity_arn`이 비면 안 뜬다 → 메일 발송 불가).

### 3-3. apply

```sh
terraform apply prod.tfplan
```

### 3-4. 출력 읽기

```sh
terraform output
```

오늘 추가된 출력: `media_bucket_name`, `media_bucket_arn` (`outputs.tf:52-60`).
둘 다 `var.media_s3_bucket`에서 파생되므로 **버킷을 만들었든 참조했든 같은 값**이 나온다.
`media_bucket_name`은 **`DJANGO_MEDIA_S3_BUCKET`과 반드시 같아야 한다**(§2-3).

### 3-5. ALB `/media/*` 라우팅 확인 — **업로드를 켜기 전 필수**

§0-3 참조. **코드는 고쳐졌지만(`web.tf`에 `/media/*` 포함), 이 확인은 삭제하지 말 것.**
이유: 실 리스너에 규칙이 붙었는지는 **apply 결과이지 코드가 아니다**. 그리고 이 항목이 틀렸을 때의
증상이 **조용하다** — 이미지가 "깨진 아이콘"이 아니라 `MediaImage`의 `onError` 폴백 때문에
**그라디언트 플레이스홀더**로 렌더돼, 배포를 보는 사람 눈에는 정상적인 디자인처럼 보인다.
**어떤 e2e도 이걸 대신 잡아주지 않는다**(CI엔 ALB가 없다 — §0-3).

**(a) 리스너 규칙에 `/media/*`가 실렸는지 — apply 직후, 업로드 켜기 전:**
```sh
ALB_ARN=$(aws elbv2 describe-load-balancers --names assen-prod-api \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text --region ap-northeast-2)
LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" \
  --query 'Listeners[?Port==`443`].ListenerArn' --output text --region ap-northeast-2)
aws elbv2 describe-rules --listener-arn "$LISTENER_ARN" --region ap-northeast-2 \
  --query 'Rules[?Priority==`100`].Conditions[].Values[]'
# → ["/api/*", "/healthz", "/readyz", "/media/*"] — /media/* 가 없으면 여기서 멈출 것
```

**(b) 실제 왕복 — 업로드를 켠 뒤:**
```sh
curl -sI "https://<prod-domain>/media/uploads/<업로드한-uuid>.png" | head -1   # 200
curl -sI "https://<prod-domain>/media/uploads/<업로드한-uuid>.png" | grep -i content-type
# → image/png. **application/octet-stream이면 200이어도 실패다** — Upload 행 조회가 안 된 것
#   (media.py의 _UNVOUCHED_CONTENT_TYPE). 브라우저가 이미지로 렌더하지 않는다.
```

> `/media/*`가 규칙에 없는 채로 `ALLOW_UPLOADS`를 켜면 업로드는 **201로 성공**하고 이미지는
> 전부 깨진다 — 오늘 고친 "1시간 뒤 깨짐"보다 나쁘다(즉시, 그리고 조용히).

### 3-6. ACM + DNS

1. ACM에서 프로덕션 도메인 인증서 발급(**ap-northeast-2**), DNS 검증 레코드 등록, `ISSUED` 확인.
2. `terraform output alb_dns_name` → 그 값으로 DNS 연결:
   - Route53: `<prod-domain>` A레코드 **Alias → ALB**
   - 외부 DNS(예: Cafe24): CNAME → ALB DNS 이름
3. 전파 확인: `dig +short <prod-domain>`

> ACM ARN이 확정된 뒤 `prod.tfvars`에 넣고 **다시 apply**해야 HTTPS 리스너가 생긴다.
> (인증서 없이 먼저 apply했다면 80이 forward로 떠 있다 — 프로덕션에서 방치 금지.)

### 3-7. GitHub Environment 값 등록

§2-4 표대로.

### 3-8. 첫 배포

§4로.

---

## 4. 릴리즈 절차 (GitOps)

`AGENTS.md:56`: **main = prod. 직접 push 금지. `dev → main` 머지가 릴리즈 게이트 — 인간 승인 필수.**

1. **`dev` → `main` PR** 생성. CI(lint+typecheck+test+build) green 확인.
2. 인간 승인 후 머지. (`main`이 프로덕션 desired state)
3. **`main` 브랜치에서** Actions → `deploy` → **Run workflow**.
   - **ref를 `main`으로 선택할 것.** 다른 브랜치를 고르면
     `deploy-prod-ecs.sh:21-24`가 **큰 소리로 실패**한다 (오전본의 R1 결함은 §0-1대로 수정됨).
   - `image_tag` 입력은 **비워 둘 것.** 이 값은 "배포할 기존 이미지 태그"가 **아니라**
     **새로 빌드할 이미지에 붙일 태그**다 (`deploy.yml:73` → `COMMIT_SHA` →
     `build-prod-image.sh:10`). 옛 SHA를 넣으면 **현재 체크아웃을 빌드해서 그 SHA
     태그를 덮어쓴다** — 롤백이 아니라 이력 훼손이다 (§6 참조).
4. **수동 승인 게이트**: Environment `production`의 required reviewer가 승인할 때까지
   런이 멈춘다. 이것이 유일한 인간 게이트다.
5. 승인 → 스크립트 진행:
   ECR 로그인 → **api + web 이미지 빌드**(`build-prod-image.sh`) →
   **4개 태그 푸시**(`api:<sha>`, `api:prod`, `web:<sha>`, `web:prod` — `:79-82`) →
   migrate 태스크 실행 후 **exit 0 확인**(`:88-129`) →
   **api/worker/beat/web 전부** `force-new-deployment`(`:132-139`) →
   `services-stable` 대기(**web 포함**, `:142-146`) → `/healthz`, `/api/health` 스모크.
6. **수동 web 절차는 없다.** (오전본 §3-5는 삭제됐다 — 파이프라인이 web을 굴린다.)

**이미지 태그 의미**
- `:<commit-sha>` = 불변(사실상). 이 릴리즈의 정체.
- `:prod` = 가변 포인터. **task definition이 참조하는 것은 이 태그다**
  (`main.tf:12` `local.image = "${repo}:${var.image_tag}"`, web은 `web.tf:25`). 그래서
  `force-new-deployment`가 `:prod`를 다시 pull한다. → 롤백 방식이 §6처럼 되는 이유.

---

## 5. 배포 후 스모크

`<HOST>` = `https://<prod-domain>`.

### 5-1. 기본 생존 (스크립트가 이미 수행 — `deploy-prod-ecs.sh:148-154`)

```sh
curl -fsS "<HOST>/healthz"        # 200
curl -fsS "<HOST>/api/health"     # 200 + JSON
```

### 5-2. HTTPS / 보안 헤더

```sh
curl -sI "http://<prod-domain>/" | head -1        # 301 (alb.tf:45-60 리다이렉트)
curl -sI "<HOST>/api/health" | grep -i strict-transport-security   # max-age=31536000
```

### 5-3. 읽기 엔드포인트 (인증 불필요)

```sh
curl -fsS "<HOST>/api/creators" | head -c 300
```

### 5-4. 인증 엔드포인트

```sh
# 소셜 로그인 시작 (GET)
# OAuth 앱이 설정됐으면 200 + {"authorize_url","state"}, 미설정이면 503 SocialUnavailable
curl -si "<HOST>/api/fan/social/kakao/start?redirect_uri=https://<prod-domain>/auth/callback" | head -1
```

> `redirect_uri`는 필수 쿼리 파라미터다. `SOCIAL_ALLOWED_REDIRECT_ORIGINS`를
> 설정했다면(`prod.tfvars`) 그 오리진과 일치해야 하고, 아니면 400이 난다.

### 5-5. **503이 정상인 것 — 200이 나오면 그것이 사고다**

아래 503은 **버그가 아니라 설계된 fail-closed**다.

| 확인 | 엔드포인트 | 기대 | 근거 |
|---|---|---|---|
| **유료 체크아웃** | `POST /api/orders` (인증+payload 필요) | **503 `PaymentsUnavailable`** — **정상.** 실 PG는 소프트런치에서 **제외된 게이트**다 | `config/payment.py:138-156` (`ENABLE_MOCK_PAYMENT`가 `base.py:120`에 하드코딩 False) |
| 결제수단 등록 | `POST /api/fan/payment-methods` | **503 `PaymentsUnavailable`** — 정상 | 위와 동일 |
| 본인인증(19+) | `/api/fan/verify/*` | **503** — 정상 (provider 미계약) | `ENABLE_MOCK_KYC=False` (`base.py:118`) |
| 배송 체크아웃 | 실물 주문 | **503 `ShippingCheckoutUnavailable`** — 정상 | `ENABLE_SHIPPING_CHECKOUT=False` (`base.py:158`) |
| 푸시 | — | **503 `PushUnavailable`** — 정상 | `ENABLE_MOCK_PUSH=False` (`base.py:150`) |
| capabilities | `GET /api/capabilities` | `payment_available: false`, `shipping_checkout_available: false` | `config/api.py:90-97` |

```sh
# mock 게이트 상태를 그대로 노출
curl -fsS "<HOST>/api/capabilities"
# → "payment_available": false  이어야 정상 (true면 프로덕션에 mock이 켜진 사고)
```

### 5-6. **켜기 전에는 503, 켠 뒤에는 200 — 두 항목**

오전본과 달리 이 둘은 **더 이상 코드 블로커가 아니다**. 설정이 붙으면 열린다.

#### (a) 이메일 가입

| 상태 | 기대 | 근거 |
|---|---|---|
| SES 미검증 / `EMAIL_SENDER_BACKEND` 미설정 | `POST /api/fan/signup/email` → **503 `EmailUnavailable`** | `identity/api.py:500-506` (`email_sender()`가 None) |
| 부분 설정(예: `EMAIL_FROM_ADDRESS` 누락) | **503** (fail-closed, 조용히) | `config/email.py:263-283` |
| **모르는 백엔드명** | **컨테이너 부팅 실패** | `prod.py:79-84` |
| SES 검증 + 샌드박스 탈출 + `EMAIL_SENDER_BACKEND=ses` | **200 + 실제 메일 수신** | `config/email.py:193-234` |

**켠 뒤 양성 확인** (샌드박스 탈출 전이면 사전 검증된 주소로만 성공한다):
```sh
curl -si -X POST "<HOST>/api/fan/signup/email" \
  -H 'Content-Type: application/json' \
  -d '{"email":"<실수신가능주소>","password":"<12자이상>","nickname":"스모크",
       "consent_terms":true,"consent_privacy":true,"age_over_14":true}' | head -1
# → 200. 메일함에서 https://<웹오리진>/verify-email?token=… 링크 수신 확인
#   ★ 링크 호스트가 WEB_BASE_URL(웹 오리진)인지 확인 — API 호스트면 설정이 틀린 것
```

#### (b) 업로드

| 상태 | 기대 | 근거 |
|---|---|---|
| `ALLOW_UPLOADS` 미설정 | `POST /api/uploads` → **503 `UploadStorageUnavailable`** — **설계된 정상** | `uploads/api.py:158-163` |
| `ALLOW_UPLOADS=true`, 버킷 없음(S3 백엔드인데 버킷명 빔) | **503** | `config/storage.py:42-69` |
| `ALLOW_UPLOADS=true` + 버킷 | **201 + `{"url": "/media/uploads/<uuid>.<ext>"}`** | `uploads/api.py:278-281` |

**켠 뒤 양성 확인 — ★ 오늘 고친 버그가 정확히 이것이다:**
```sh
# 1) 업로드 → 201 + site-relative URL
URL=$(curl -fsS -X POST "<HOST>/api/uploads" -H "Authorization: Bearer <token>" \
  -F "file=@tiny.png;type=image/png" | python -c 'import sys,json;print(json.load(sys.stdin)["url"])')
echo "$URL"   # → /media/uploads/<uuid>.png  (절대 URL도 서명도 없어야 정상)

# 2) 그 URL이 실제로 이미지를 돌려주는지 (★§0-3이 안 고쳐졌으면 여기서 404)
curl -sI "<HOST>${URL}" | head -1                       # 200
curl -sI "<HOST>${URL}" | grep -i content-type          # image/png (octet-stream 아님)

# 3) ★★ 1시간 뒤 같은 URL이 여전히 200인지 — 이것이 오늘 고친 회귀다.
#    예전에는 Upload.url에 ~1h 만료 S3 서명 URL을 저장해서 모든 이미지가 1시간 뒤 깨졌다.
#    지금 URL은 스토리지 키의 순수 함수라 만료가 없다(apps/uploads/services.py:267-281).
sleep 3600; curl -sI "<HOST>${URL}" | head -1           # 200 이어야 정상
```

**모더레이션 테이크다운 양성 확인** (`apps/uploads/services.py:180-220`):
```sh
# 팬/운영자가 upload_id를 실어 신고 → 기존 safety 트리아지 큐에 들어온다
curl -fsS "<HOST>/api/safety/reports" -H "Authorization: Bearer <operator-token>"   # 큐 조회

# actioned로 넘기면 객체가 quarantine/ 키로 이동 → 서빙 키는 즉시 404
curl -fsS -X PATCH "<HOST>/api/safety/reports/<id>/status" \
  -H "Authorization: Bearer <operator-token>" -H 'Content-Type: application/json' \
  -d '{"status":"actioned"}'
curl -sI "<HOST>${URL}" | head -1                        # 404 (403 아님 — 의도적)

# 되돌리면 복구된다. 바이트는 절대 삭제되지 않는다.
```

### 5-7. 로그 확인

```sh
aws logs tail /ecs/assen-prod/api --since 10m --region ap-northeast-2
```

`DEBUG=False`, JSON 한 줄/레코드(`prod.py:117`)인지 확인.

> 실 메일 발송 로그에는 **PII도 토큰도 없다** — 도메인만 남는다
> (`config/email.py:134-143`). `email.ses.verification_sent`가 보이면 정상.

### 5-8. **채널 레이어가 redis인지 확인 (조용히 깨지는 항목)**

`base.py`의 `_build_channel_layers()`는 **fail-safe**다 — `CHANNEL_LAYERS_BACKEND`
오타, `CHANNEL_LAYERS_REDIS_URL` 누락, `channels_redis` 미설치 중 **어느 하나라도** 걸리면
**부팅 에러 없이 조용히** 단일 프로세스 `InMemoryChannelLayer`로 되돌아간다.
`api_desired_count=2`이므로 그 경우 실시간 알림이 **같은 태스크에 붙은 팬에게만** 간다
(겉보기엔 "가끔 알림이 안 온다"로 보인다).

> **미검증**: 이 terraform 스택은 ECS Exec(`enable_execute_command`)를 켜지 않는다
> (`ecs.tf`에 해당 설정 없음). Exec 없이 확인하려면 **서로 다른 두 태스크에 WebSocket을
> 붙여 놓고** 알림을 발생시켜 양쪽 모두 수신되는지 보는 것이 유일한 실측 방법이다.

---

## 6. 롤백

> ⚠️ **`deploy.yml`을 옛 SHA로 재실행하는 것은 롤백이 아니다** (§4-3).
> task definition이 가변 `:prod` 태그를 가리키므로(`main.tf:12`, `web.tf:25`),
> **롤백 = ECR에서 `:prod`를 이전 이미지로 다시 붙이고 서비스를 강제 롤**하는 것이다.
> (`deploy.yml:17-22`의 `image_tag` 설명도 이제 이 사실을 명시한다.)

```sh
REGION=ap-northeast-2; GOOD=<되돌릴 커밋 SHA 태그>

# api·web 두 리포 모두 되돌린다 — 이제 둘 다 파이프라인이 굴리므로 함께 전진했다.
for REPO in assen-platform-api assen-platform-web; do
  MANIFEST="$(aws ecr batch-get-image --repository-name $REPO \
    --image-ids imageTag=$GOOD --query 'images[0].imageManifest' \
    --output text --region $REGION)"
  aws ecr put-image --repository-name $REPO --image-tag prod \
    --image-manifest "$MANIFEST" --region $REGION
done

# 서비스 강제 롤 → :prod 재pull
for SVC in assen-prod-api assen-prod-worker assen-prod-beat assen-prod-web; do
  aws ecs update-service --cluster assen-prod --service $SVC \
    --force-new-deployment --region $REGION >/dev/null
done
aws ecs wait services-stable --cluster assen-prod \
  --services assen-prod-api assen-prod-worker assen-prod-beat assen-prod-web --region $REGION

# 스모크
curl -fsS "https://<prod-domain>/api/health"
```

**마이그레이션은 자동으로 되돌아가지 않는다.** 롤백 대상 릴리즈가 스키마를
바꿨다면 이미지 롤백만으로는 부정합이 남는다. 역마이그레이션은 사람이 판단해
`migrate <app> <이전번호>`를 별도 one-off 태스크로 실행해야 한다. → **미검증**
(실제 적용 이력 없음).

**긴급 정지** (트래픽 차단):
```sh
aws ecs update-service --cluster assen-prod --service assen-prod-api \
  --desired-count 0 --region ap-northeast-2
```
> `ecs.tf:160`이 `desired_count`를 `ignore_changes`에 두므로 다음 apply가
> 이 값을 되돌리지 않는다 (web도 동일 — `web.tf:105`).

---

## 7. 알려진 제약

### 설계된 fail-closed (정상 — 대표 승인된 소프트런치 스코프)

- **실 PG 결제 없음** → 유료 체크아웃/구독/결제수단 전부 **503 `PaymentsUnavailable`**.
  `ENABLE_MOCK_PAYMENT`는 `base.py:120`에 **하드코딩 False**(env로 못 켬)이고
  `prod.py`가 덮지 않는다. `require_payment_available()`(`config/payment.py:138`)은
  토크나이저가 아니라 **플래그**를 본다 — 실 토크나이저만 꽂아도 무결제 PAID가 새지
  않도록 한 containment (ASS-286). PG 가맹 계약 후 별도 작업.
- **실 19+ 본인인증 없음** → `ENABLE_MOCK_KYC=False`(`base.py:118`) → 본인인증 503,
  `ENABLE_ADULT_CONTENT=False`(`base.py:119`) → adult_only 콘텐츠는 **전원에게 숨김**.
  provider 계약 + 법무 사인 후.
- **배송 체크아웃 없음** → `ENABLE_SHIPPING_CHECKOUT=False`(`base.py:158`, 하드코딩)
  → 실물 주문 503. 배송 개인정보 처리방침 승인 게이트(ASS-287 A-1).
- **푸시 없음** → `ENABLE_MOCK_PUSH=False`(`base.py:150`) → 503.
- **법무 페이지 사인오프 대기** (약관/개인정보/청소년보호).

### 콘텐츠 모더레이션 posture (대표 승인 07-18)

**신고 기반 사람 테이크다운**이 최소 실행 가능 posture다. 자동 스캔은 아니다.

- 이미지는 하드 검증(매직바이트 + Pillow decode-verify + 압축폭탄/치수 가드 +
  메타데이터 전량 제거)을 통과하면 **수락**된다 (`apps/uploads/api.py`).
- 팬/운영자 신고가 **`upload_id`를 실어** 들어오고, **기존 safety 트리아지 큐**
  (`GET /api/safety/reports`)가 그대로 그 큐다 (`apps/safety/api.py:347-351`).
- `PATCH /api/safety/reports/{id}/status` → `actioned`이면
  **객체를 `quarantine/` 키로 이동**한다 (`apps/uploads/services.py:180-220`):
  서빙 키가 스토어에서 404가 되어 **미결 서명 URL까지 한꺼번에 무효화**된다.
  역전이하면 복구된다. **바이트는 절대 삭제되지 않는다.**
- **자동 provider 스캔**(nudity/CSAM)은 여전히 **대표·법무 게이트**다.
  플러그인 자리만 있다 (`apps/uploads/api.py:116-134` `_moderation_accepts`).

> ✅ **`infra/terraform/media.tf`의 버저닝 주석 — 수정됨(2026-07-17).** 그 주석은 버저닝을 켠
> 근거로 "테이크다운은 DB 상태 변경뿐이고 객체를 **이동·복사·삭제하지 않는다**, 태스크 롤의
> `s3:DeleteObject`는 **호출처가 없다**"고 적고 있었으나, 실제로는 `services.py:135-177`의
> `_move_object()`가 `save()` 후 **`default_storage.delete(source)`를 호출**한다 —
> 테이크다운/복구 **양방향 모두** 삭제 호출처다. **결정(버저닝 ON)은 그대로**이고 오히려 더
> 정당해졌으므로(이제 실제 삭제 경로가 존재한다), **리소스는 손대지 않고 근거만** 실제 코드에
> 맞게 다시 썼다. 같은 파일의 lifecycle 주석도 동일한 낡은 전제("앱은 삭제하지 않으므로
> noncurrent 버전은 쌓이지 않는다")를 갖고 있어 함께 정정했다 — 실제로는 테이크다운마다
> 하나씩 쌓이며, **그 noncurrent 버전이 바로 복구 그물**이다(그래서 만료 룰을 두면 안 된다).

### 미디어를 앱 티어로 프록시하는 것의 배포상 귀결

오늘부터 **모든 미디어 바이트가 ECS를 통과**한다 (`apps/uploads/media.py`).
버킷 다이렉트가 아니다. 이것이 URL을 안정시키고 테이크다운을 즉시로 만드는 대가다.

- **ALB idle timeout**: `alb.tf`가 이제 **`idle_timeout = 120`을 명시**한다(기본 60초에서 상향).
  근거는 `alb.tf`의 주석 참조 — 요지: idle 타이머는 **바이트가 전혀 안 움직일 때만** 발화하므로
  *느린* 전송은 청크마다 리셋되어 걸리지 않는다. 60초가 위험한 것은 **stall**(셀 핸드오버·터널·
  앱 백그라운드)로, 재개했을 때 ALB가 이미 연결을 끊어놓은 경우다 — 나가는 쪽은 깨진 이미지,
  들어오는 쪽은 **10 MiB**(`UPLOAD_MAX_BYTES`, `base.py:455`) 재전송이다.
  daphne는 `--http-timeout` 기본이 None(`Dockerfile`의 CMD도 미설정)이라 타깃이 먼저 연결을
  닫지 않으므로, 상향이 keep-alive 경쟁으로 인한 502를 만들지 않는다. → **실측은 여전히 없음**
  (실 트래픽에서 120이 충분한지는 소프트런치 후 관측할 것).
- **인그레스 바디 캡**: 업로드 **방향**의 캡은 유지할 것. 앱단 캡은 멀티파트 파서가
  바디를 다 읽은 뒤에야 동작한다(`apps/uploads/api.py:256-259` 주석) — 진짜 조기 차단은
  리버스 프록시/ALB 층 몫이다.
- **응답은 청크 스트리밍**이다 (`media.py:99-102` `StreamingHttpResponse`) →
  **`Content-Length` 없음, Range 미지원**. 비디오 seek 같은 것은 오늘 불가.
- **버킷은 프라이빗 유지** — 앱 티어가 유일한 독자다.
- **CDN을 `/media/` 앞에 두면 purge-on-takedown이 필수 요구사항이 된다.**
  지금 테이크다운이 즉시인 이유가 정확히 "프록시라서 퍼지할 엣지 사본이 없다"이다.
  응답과 저장 객체 모두 `Cache-Control: private`이라 공용 캐시는 오늘 막혀 있다
  (`media.py:115`). → CDN 도입은 **모더레이션 재설계를 동반**한다.

### 🔴 코드 수정 필요 (이번 범위 밖, 별도 승인 요망)

**R3. `ecr.tf`의 고쳐진 lifecycle 정책이 실 리포에 닿지 않는다** — ✅ **조회 완료(위험 없음)**
`ecr.tf:59-75`의 정책(untagged 14일 만료, `:prod`는 어떤 룰에도 안 걸림)은 **옳지만
실 리포에 적용되지 않는다**: `prod.tfvars`/`dev.tfvars` 모두 `create_ecr_repository=false`이고,
정책 리소스는 `count = var.create_ecr_repository ? 1 : 0`이라 **생성 자체가 되지 않는다**
(코드로 확인됨).

**실 리포에 무엇이 붙어 있는지 — 2026-07-17 직접 조회함(더 이상 미검증 아님).**

```sh
aws ecr get-lifecycle-policy --repository-name assen-platform-api --region ap-northeast-2
aws ecr get-lifecycle-policy --repository-name assen-platform-web --region ap-northeast-2
# → 두 리포 모두 LifecyclePolicyNotFoundException
```

**결과: 양 리포 모두 lifecycle 정책이 없다.**

| 무엇 | 결론 |
|---|---|
| 옛 `tagStatus: any` + `imageCountMoreThan: 20`이 붙어 있나 | **아니다.** → **프로덕션 이미지 만료 위험은 존재하지 않는다.** 오전본 R3의 우려는 실현되지 않았다 |
| 그럼 무엇이 남나 | **무한 스토리지 증가뿐.** untagged 레이어와 은퇴한 sha 이미지가 정리되지 않고 누적된다(R4) |
| 배포 전 블로커인가 | **아니다.** 비용 항목이지 안전 항목이 아니다 |

> **성격**: 시점 관측(2026-07-17, 읽기 전용 `get-lifecycle-policy` 1회, 계정 793451441183).
> 정책은 콘솔에서 누구나 붙일 수 있고 terraform이 이 리포들을 관리하지 않으므로
> **이 사실은 시간이 지나면 낡을 수 있다**. 정책을 새로 붙일 때는 `ecr.tf:59-75`의 내용
> (untagged만 만료)을 쓸 것 — 옛 `tagStatus: any` 형태를 붙이면 dev 푸시 20번에
> 살아있는 `:prod`가 만료 대상이 되어 스케일아웃/롤백 시 pull이 실패한다.

**R4. 은퇴한 commit-sha 이미지는 어떤 정책으로도 정리 못 한다**
`ecr.tf:41-58`이 근거를 상세히 적어 뒀다: 태깅 스킴이 bare hex sha라 ECR의
tag-prefix 선택으로는 "은퇴한 sha"와 "살아있는 prod sha"를 구분할 수 없다.
정리하려면 **태깅 변경**(`prod-<sha>` / `dev-<sha>`)이 필요하고, 그건 이 런북의
롤백 계약(§6)을 바꾼다 → 의도적 후행. 그때까지 손으로 정리(~$0.10/GB-월).

### 확실하지 않은 것 (미검증)

- terraform이 **한 번도 apply된 적 없다** → 계정별 쿼터/IAM 경계/정확한 secret ARN은
  첫 apply에서만 드러난다. **`media.tf`는 오늘 새로 쓰였으므로 특히 미검증**이다.
- 프로덕션 계정이 dev/staging과 **같은 계정(793451441183)인지 별도 계정인지 미확정**.
  같으면 `create_ecr_repository=false`(현재 `prod.tfvars` 설정)가 맞고,
  다르면 `true`로 바꾸고 `image_repository_url`/`web_image_repository_url`을 지워야 한다.
- 프로덕션 **도메인 미확정** (`assenent.com`은 랜딩용). → ACM·`WEB_BASE_URL`·
  `ASSEN_PROD_API_URL`·`DJANGO_ALLOWED_HOSTS` 전부 이것에 묶여 있다.
- **SES 샌드박스 탈출 리드타임 미상** (AWS 지원 응답 시간에 달림). 소프트런치
  일정의 임계경로일 수 있다.
- `web_api_internal_url`을 공개 HTTPS 도메인으로 두면 SSR fetch가 ALB를 **헤어핀**한다.
  동작은 하지만 지연이 붙는다. HTTP 80은 ACM 설정 시 301 리다이렉트라
  dev식 `http://<alb-dns>/api`는 **쓸 수 없다**. 내부 전용 경로가 필요하면 별도 설계 필요.
- 미디어 프록시의 ALB idle timeout **실측** (위 §7). 값은 이제 120으로 **명시**됐지만, 그 값이
  실 모바일 트래픽에 충분한지는 관측된 바 없다 — 근거 있는 추정이지 측정치가 아니다.
- **실 리스너에 `/media/*` 규칙이 붙는지**는 apply 후에만 확인된다(§3-5). 코드는 맞지만
  **어떤 자동 테스트도 이걸 커버하지 않는다**(CI엔 ALB가 없다).
- 롤백 시 역마이그레이션 절차.
