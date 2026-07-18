# 신방향 도메인 ERD (B1 — 참조용)

> **코드 = 정본**(SDLC 09 §3): 본 다이어그램은 `server/apps/{creator,social,content,commerce,membership}/models.py` +
> `identity.Account`의 **참조용 투영**이다. 모델 변경 시 이 문서를 갱신한다.
> 마이그레이션 정식 전환 완료(2026-07-09, #25 승인 하) — 모델 보유 앱은 각자 `0001_initial`을 보유하고,
> 테이블은 `migrate`로 생성된다(server/AGENTS.md). 모델 변경 시 `makemigrations`로 갱신, `makemigrations --check`는 항상 clean이어야 한다.

```mermaid
erDiagram
    ACCOUNT ||--o| CREATOR : "owner (1:1, nullable)"
    ACCOUNT ||--o{ FOLLOW : follower
    CREATOR ||--o{ FOLLOW : "followers"
    CREATOR ||--o{ POST : "posts"
    POST ||--o{ COMMENT : "comments"
    POST ||--o{ LIKE : "likes"
    ACCOUNT ||--o{ COMMENT : "author (nullable)"
    ACCOUNT ||--o{ LIKE : user
    CREATOR ||--o{ PRODUCT : "products (nullable FK)"
    CREATOR ||--o{ MEMBERSHIP_TIER : "tiers (nullable FK)"

    ACCOUNT {
        int id PK
        uuid fan_id UK "외부 안정 식별자"
        string role "fan|cast|operator|manager|admin|system"
        string nickname "표시명"
        string auth_subject_hash "부분 unique(비어있지 않을 때)"
        bool is_active
    }
    CREATOR {
        uuid id PK
        string handle UK "슬러그 ^[a-z0-9_]+$"
        string name
        text bio
        string accent_color "hex — creatorAccent"
        string avatar_url
        string cover_url
        string category "idx"
        bool verified
    }
    FOLLOW {
        uuid id PK
        fk follower "Account, CASCADE"
        fk creator "Creator, CASCADE"
        datetime created_at
    }
    POST {
        uuid id PK
        fk creator "Creator, CASCADE"
        text body
        string media_url "스칼라 — Media 모델은 업로드 도입 시"
        datetime created_at "idx(-created_at)"
    }
    COMMENT {
        uuid id PK
        fk post "Post, CASCADE"
        fk author "Account, SET_NULL nullable"
        string author_name "표시명 비정규화(공개 API는 이것만 노출)"
        text body
        datetime created_at
    }
    LIKE {
        uuid id PK
        fk post "Post, CASCADE"
        fk user "Account, CASCADE"
        datetime created_at
    }
    PRODUCT {
        uuid id PK
        fk creator "Creator, CASCADE nullable"
        string type "goods|digital|experience|ticket|coupon"
        string title
        int price "정수 KRW 표시값(정산 아님)"
        string meta
        string media_url
    }
    MEMBERSHIP_TIER {
        uuid id PK
        fk creator "Creator, CASCADE nullable"
        string name
        int price "정수 KRW/period 표시값"
        string period
        json benefits "list[str]"
        string badge
        bool featured
        int sort_order
    }
```

**Unique 제약**: `FOLLOW(follower, creator)` · `LIKE(post, user)` — DB 레벨 중복 방지.
**파생 카운트**(저장 안 함): Creator.followers/posts, Post.like_count/comment_count — API에서 `annotate`.
**게이트로 부재하는 엔티티**: Order/OrderItem/Inventory(B7) · Subscription/Settlement(B4/B7) ·
Conversation/Message/Presence(B6) · AgeVerification(B3) — 도입 시 본 ERD 확장.
**차단(Block)**: 별도 모델 없음 — 기존 `safety.UserBlock` 재사용(SDLC 09 §8).
