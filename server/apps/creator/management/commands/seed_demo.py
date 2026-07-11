"""Seed the new-direction demo data, mirroring the web frontend mock (E11/B1·B4).

Idempotent: keyed on natural keys (creator handle, post body, product title,
tier name, account username / phone-hash) so re-running does not duplicate.

This is a **partial** mirror of ``web/src/lib/api/index.ts`` — close enough that
the B5 mock→API swap is drop-in for the seeded surfaces, but not a byte-for-byte
1:1. Intentional differences are called out inline with NOTE comments so the drift
is deliberate, not accidental:

    python manage.py seed_demo

NOTE (differences from the web mock):
- The web mock's locked *post* (po2) is not seeded — the ``Post`` model has no
  ``locked`` field, so a locked-post flag is out of this command's scope.
- The web mock numbers products p1..pN on its own scheme; the server keys products
  by (creator, title), so the p-numbers do not line up 1:1 (e.g. the web coupon is
  "p7"). The coupon listing below mirrors the web welcome-coupon product.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.commerce.models import Product
from apps.content.models import Comment, Post
from apps.creator.models import Creator
from apps.identity.models import Account, Role
from apps.identity.signup_services import hash_phone, normalize_phone
from apps.membership.models import MembershipTier
from apps.social.models import Follow

# (handle, name, category, verified, accent_color, bio)
_CREATORS = [
    ("stellar", "별빛 일러스트", "일러스트", True, "#E14B8A", "별빛이 흐르는 일러스트를 그립니다."),
    ("neonbeats", "Neon Beats", "뮤직", False, "#3B82F6", ""),
    ("rabbit", "토끼방송국", "버튜버", False, "#F59E0B", ""),
    ("myo", "묘화가", "일러스트", False, "#10B981", ""),
    ("lumi", "Studio Lumi", "굿즈", False, "#8B5CF6", ""),
]

# (handle, body)
_POSTS = [
    ("stellar", "신작 공개! 많은 관심 부탁드려요."),
    ("stellar", "다음 주 팬미팅 신청 받아요."),
    ("rabbit", "오늘 저녁 8시 라이브 켜요! 놀러오세요 🐰"),
    ("neonbeats", "새 EP 티저 공개 🎧"),
    ("myo", "냥이 그림 모음집 작업 중 🐱"),
    ("lumi", "굿즈 재입고 안내드립니다."),
]

# (post body, author_name, comment body)
_COMMENTS = [
    ("신작 공개! 많은 관심 부탁드려요.", "팬 하나", "응원합니다! 항상 잘 보고 있어요"),
    ("신작 공개! 많은 관심 부탁드려요.", "루미덕후", "다음 작품도 기대할게요 🙌"),
    ("다음 주 팬미팅 신청 받아요.", "팬 셋", "신청 완료했어요!"),
    ("오늘 저녁 8시 라이브 켜요! 놀러오세요 🐰", "토끼팬", "기다렸어요!!"),
]

# Product catalog, mirroring the web mock's extended detail fields.
# (handle, type, title, price, meta, description, options, stock, sold_out, locked)
# A blank handle ("") seeds a global (creatorless) catalog listing.
# NOTE: no realtime 1:1 video-call item — `future.video_call` is off/forbidden in
# P0/P1 (Technical Architecture). The 브러시팩 is a membership-locked listing, the
# 피규어 is sold out, and the 웰컴 쿠폰 is a global (no-creator) coupon mirroring
# the web mock's "p7" welcome-coupon product.
_PRODUCTS = [
    ("stellar", "goods", "아크릴 스탠드", 18000, "한정 200개",
     "별빛 일러스트 아크릴 스탠드입니다.", ["A타입", "B타입"], 120, False, False),
    ("stellar", "digital", "고해상도 화보집", 9900, "다운로드",
     "풀 해상도 디지털 화보집 (PDF).", [], None, False, False),
    ("stellar", "experience", "포토카드 팬사인", 30000, "선착순 20",
     "1:1 포토카드 팬사인 이벤트.", [], 20, False, False),
    ("neonbeats", "digital", "새 EP 음원팩", 12000, "MP3+FLAC",
     "신규 EP 고음질 음원 번들.", ["MP3", "FLAC"], None, False, False),
    ("rabbit", "ticket", "온라인 팬미팅", 25000, "12/24 20:00",
     "라이브 온라인 팬미팅 입장권.", [], 100, False, False),
    ("myo", "goods", "냥이 스티커팩", 6000, "10종",
     "손그림 고양이 스티커 10종 세트.", [], 300, False, False),
    ("lumi", "goods", "굿즈 키링", 8000, "신상",
     "스튜디오 루미 아크릴 키링.", ["핑크", "블루"], 80, False, False),
    ("stellar", "digital", "멤버 전용 브러시팩", 15000, "멤버십",
     "멤버십 구독자 전용 브러시 리소스.", [], None, False, True),
    ("lumi", "goods", "한정 피규어", 45000, "품절",
     "완판된 한정판 피규어.", [], 0, True, False),
    ("", "coupon", "웰컴 10% 할인 쿠폰", 3000, "30일 유효",
     "첫 구매를 위한 10% 할인 쿠폰. 발급 후 30일간 사용할 수 있습니다.", [], None, False, False),
]

# (name, price, period, benefits, badge, featured, sort_order) — attached to stellar.
_TIERS = [
    ("라이트", 4900, "월", ["전용 포스트", "멤버 뱃지"], "", False, 0),
    ("스탠다드", 9900, "월", ["라이트 혜택 전부", "고해상도 화보", "월간 라이브"], "인기", True, 1),
    ("프리미엄", 19900, "월", ["스탠다드 전부", "팬사인 우선", "한정 굿즈 우선"], "", False, 2),
]

# The primary demo fan (mirrors the web mock session). Phone → auth_subject_hash so
# it can log in through the mock-OTP fan login flow with this number.
_DEMO_FAN_PHONE = "010-0000-0001"
_DEMO_FAN_NICKNAME = "데모팬"
_DEMO_CREATOR_PHONE = "010-0000-0002"
_DEMO_CREATOR_NICKNAME = "데모크리에이터"

# 시드 엔티티 id는 **재시드 간 결정적**(uuid5)이어야 한다 — 웹 시각 회귀(e2e/visual.spec)의
# seed 그라디언트가 엔티티 id에서 파생되므로(web/src/lib/placeholder gradientStyle), id가
# 재시드마다 바뀌면 스크린샷 베이스라인이 흔들린다. 자연키에서 파생해 멱등성과도 일관.
_SEED_NS = uuid.uuid5(uuid.NAMESPACE_URL, "assen:seed_demo")


def _seed_id(kind: str, key: str) -> uuid.UUID:
    """Deterministic per-entity UUID derived from the entity's natural key."""
    return uuid.uuid5(_SEED_NS, f"{kind}:{key}")


def _guard_demo_seed() -> None:
    """Refuse to seed demo data outside an explicitly opted-in mock environment.

    ``seed_demo`` writes demo accounts/creators/products; running it against a real
    database pollutes production (ASS-288). Three independent guards must all pass:

    1. a non-prod (mock) profile — a hardened/prod profile has every mock gate off,
       so ``ENABLE_MOCK_FAN_OTP`` being False means "refuse outright";
    2. an explicit opt-in — ``ALLOW_DEMO_SEED=1`` in the environment;
    3. a disposable-looking database — sqlite, or a NAME marked demo/dev/test/e2e,
       so a real prod DB carrying a mock profile by misconfiguration is still refused.
    """
    if not settings.ENABLE_MOCK_FAN_OTP:
        raise CommandError(
            "seed_demo is refused on a non-mock (prod-like) profile (ASS-288)."
        )
    if os.environ.get("ALLOW_DEMO_SEED") != "1":
        raise CommandError(
            "seed_demo requires ALLOW_DEMO_SEED=1 — an explicit opt-in to writing "
            "demo data (ASS-288)."
        )
    default_db = settings.DATABASES["default"]
    db_name = str(default_db.get("NAME", ""))
    is_disposable = "sqlite" in str(default_db.get("ENGINE", "")) or any(
        marker in db_name.lower() for marker in ("demo", "dev", "test", "e2e")
    )
    if not is_disposable:
        raise CommandError(
            f"seed_demo refused: database {db_name!r} is not a demo/dev/test target "
            "(ASS-288). Point at a disposable demo DB."
        )


class Command(BaseCommand):
    """Populate demo creators, owners, posts, comments, products, tiers, and a fan."""

    help = "Seed new-direction demo data (idempotent)."

    def handle(self, *args: Any, **options: Any) -> None:
        """Create the demo graph, keyed on natural keys so re-runs are safe."""
        del args, options
        _guard_demo_seed()
        creators: dict[str, Creator] = {}
        for handle, name, category, verified, accent, bio in _CREATORS:
            creator, _ = Creator.objects.get_or_create(
                handle=handle,
                defaults={
                    "id": _seed_id("creator", handle),
                    "name": name,
                    "category": category,
                    "verified": verified,
                    "accent_color": accent,
                    "bio": bio,
                },
            )
            creators[handle] = creator
            # Each creator is operated by its own (demo) owner account.
            if creator.owner is None:
                owner, _ = Account.objects.get_or_create(
                    username=f"owner_{handle}",
                    defaults={"role": Role.FAN.value, "nickname": name},
                )
                creator.owner = owner
                creator.save(update_fields=["owner"])

        posts: dict[str, Post] = {}
        for handle, body in _POSTS:
            post, _ = Post.objects.get_or_create(
                creator=creators[handle],
                body=body,
                defaults={"id": _seed_id("post", f"{handle}:{body}")},
            )
            posts[body] = post

        for post_body, author_name, body in _COMMENTS:
            Comment.objects.get_or_create(
                post=posts[post_body], author_name=author_name, body=body
            )

        for (
            handle, type_, title, price, meta, description, option_labels, stock, sold_out, locked
        ) in _PRODUCTS:
            Product.objects.get_or_create(
                # A blank handle is a global (creatorless) catalog listing.
                creator=creators[handle] if handle else None,
                title=title,
                defaults={
                    "id": _seed_id("product", f"{handle}:{title}"),
                    "type": type_,
                    "price": price,
                    "meta": meta,
                    "description": description,
                    "options": option_labels,
                    "stock": stock,
                    "sold_out": sold_out,
                    "locked": locked,
                    # Studio visibility (R3): a sold-out seed lists as 'soldout',
                    # everything else 'selling'. No seed item is draft/hidden/adult.
                    "status": "soldout" if sold_out else "selling",
                },
            )

        stellar = creators["stellar"]
        for name, price, period, benefits, badge, featured, order in _TIERS:
            MembershipTier.objects.get_or_create(
                creator=stellar,
                name=name,
                defaults={
                    "id": _seed_id("tier", f"stellar:{name}"),
                    "price": price,
                    "period": period,
                    "benefits": benefits,
                    "badge": badge,
                    "featured": featured,
                    "sort_order": order,
                },
            )

        # A demo creator login (phone-keyed so OTP login is deterministic), set as
        # stellar's owner — lets the studio catalog/profile write flows be exercised
        # end-to-end (the auto-created owner_* accounts have no phone, so cannot log in).
        creator_phone_hash = hash_phone(normalize_phone(_DEMO_CREATOR_PHONE))
        demo_creator_account, _ = Account.objects.get_or_create(
            auth_subject_hash=creator_phone_hash,
            defaults={
                "role": Role.FAN.value,
                "nickname": _DEMO_CREATOR_NICKNAME,
                "auth_method": "phone",
            },
        )
        stellar_creator = creators["stellar"]
        stellar_creator.owner = demo_creator_account
        stellar_creator.save(update_fields=["owner"])

        # The primary demo fan, keyed on the phone-hash so login is deterministic.
        phone_hash = hash_phone(normalize_phone(_DEMO_FAN_PHONE))
        demo_fan, _ = Account.objects.get_or_create(
            auth_subject_hash=phone_hash,
            defaults={
                "role": Role.FAN.value,
                "nickname": _DEMO_FAN_NICKNAME,
                "auth_method": "phone",
                # R3: the demo fan starts un-verified (fail-closed) — the 19+ gate
                # hides adult items until they run the (mock) 본인인증 flow.
                "adult_verified": False,
                "kyc_status": "unverified",
            },
        )
        for handle in ("stellar", "rabbit"):
            Follow.objects.get_or_create(follower=demo_fan, creator=creators[handle])

        self.stdout.write(
            self.style.SUCCESS(
                f"seeded: {Creator.objects.count()} creators, {Post.objects.count()} posts, "
                f"{Comment.objects.count()} comments, {Product.objects.count()} products, "
                f"{MembershipTier.objects.count()} tiers, {Follow.objects.count()} follows, "
                f"demo fan '{demo_fan.nickname}'"
            )
        )
