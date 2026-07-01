"""Seed the new-direction demo data, mirroring the web frontend mock (E11/B1).

Idempotent: keyed on natural keys (creator handle, post body, product title,
tier name) so re-running does not duplicate. Mirrors
``web/src/lib/api/index.ts`` so the B5 mock→API swap is 1:1.

    python manage.py seed_demo
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.commerce.models import Product
from apps.content.models import Comment, Post
from apps.creator.models import Creator
from apps.identity.models import Account, Role
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

# Catalog attached to the primary demo creator (stellar): (type, title, price, meta)
# NOTE: no realtime 1:1 video-call item — `future.video_call` is off/forbidden in
# P0/P1 (Technical Architecture), so the demo must not publish it as a purchasable
# offering. Non-gated experiences only.
_PRODUCTS = [
    ("goods", "아크릴 스탠드", 18000, "한정 200개"),
    ("digital", "고해상도 화보집", 9900, "다운로드"),
    ("experience", "포토카드 팬사인", 30000, "선착순 20"),
    ("ticket", "온라인 팬미팅", 25000, "12/24 20:00"),
]

# (name, price, period, benefits, badge, featured, sort_order)
_TIERS = [
    ("라이트", 4900, "월", ["전용 포스트", "멤버 뱃지"], "", False, 0),
    ("스탠다드", 9900, "월", ["라이트 혜택 전부", "고해상도 화보", "월간 라이브"], "인기", True, 1),
    ("프리미엄", 19900, "월", ["스탠다드 전부", "팬사인 우선", "한정 굿즈 우선"], "", False, 2),
]


class Command(BaseCommand):
    """Populate demo creators, posts, comments, products, and tiers."""

    help = "Seed new-direction demo data (idempotent)."

    def handle(self, *args: Any, **options: Any) -> None:
        """Create the demo graph, keyed on natural keys so re-runs are safe."""
        del args, options
        creators: dict[str, Creator] = {}
        for handle, name, category, verified, accent, bio in _CREATORS:
            creator, _ = Creator.objects.get_or_create(
                handle=handle,
                defaults={
                    "name": name,
                    "category": category,
                    "verified": verified,
                    "accent_color": accent,
                    "bio": bio,
                },
            )
            creators[handle] = creator

        posts: dict[str, Post] = {}
        for handle, body in _POSTS:
            post, _ = Post.objects.get_or_create(creator=creators[handle], body=body)
            posts[body] = post

        for post_body, author_name, body in _COMMENTS:
            Comment.objects.get_or_create(
                post=posts[post_body], author_name=author_name, body=body
            )

        stellar = creators["stellar"]
        for type_, title, price, meta in _PRODUCTS:
            Product.objects.get_or_create(
                creator=stellar,
                title=title,
                defaults={"type": type_, "price": price, "meta": meta},
            )

        for name, price, period, benefits, badge, featured, order in _TIERS:
            MembershipTier.objects.get_or_create(
                creator=stellar,
                name=name,
                defaults={
                    "price": price,
                    "period": period,
                    "benefits": benefits,
                    "badge": badge,
                    "featured": featured,
                    "sort_order": order,
                },
            )

        # A couple of demo fans following creators, so follower counts are > 0.
        fans = [
            Account.objects.get_or_create(
                username=f"demo_fan_{i}", defaults={"role": Role.FAN.value}
            )[0]
            for i in range(2)
        ]
        for fan in fans:
            for handle in ("stellar", "rabbit"):
                Follow.objects.get_or_create(follower=fan, creator=creators[handle])

        self.stdout.write(
            self.style.SUCCESS(
                f"seeded: {Creator.objects.count()} creators, {Post.objects.count()} posts, "
                f"{Comment.objects.count()} comments, {Product.objects.count()} products, "
                f"{MembershipTier.objects.count()} tiers, {Follow.objects.count()} follows"
            )
        )
