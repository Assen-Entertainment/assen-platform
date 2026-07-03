"""서버 단독 E2E 저니 스모크 (R2 — B3/B4 런타임 검증).

로그인(OTP) → me → 팔로우 → 피드/좋아요 → 댓글 → 구독 → 주문 → 알림 → 로그아웃을
실 HTTP로 검증한다. dev(mock OTP)·seed_demo 전제. 사용:
    python scripts/api_journey_smoke.py [base_url]
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
PHONE = "010-0000-0001"


def otp_for(phone: str) -> str:
    """MockOtpSender와 동일한 결정적 코드 — normalize_phone(+82 폴딩) 기준."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    core = "82" + digits[1:] if digits.startswith("0") else digits
    normalized = "+" + core
    digest = hmac.new(b"assen-dev-otp", normalized.encode(), hashlib.sha256)
    return str(int(digest.hexdigest()[:8], 16) % 1_000_000).zfill(6)


def call(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict | list]:
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=15) as resp:
            payload = resp.read()
            return resp.status, json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        return exc.code, json.loads(payload) if payload else {}


def expect(cond: bool, label: str, detail: object = "") -> None:
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {label} {detail if not cond else ''}")
    if not cond:
        sys.exit(1)


def main() -> None:
    # 1. 로그인 (기존 시드 계정)
    status, out = call("POST", "/api/fan/login", {"phone": PHONE, "otp_code": otp_for(PHONE), "web": False})
    expect(status == 200 and bool(out.get("access_token")), "login", (status, out))
    token = out["access_token"]

    # 2. me
    status, me = call("GET", "/api/fan/me", token=token)
    expect(status == 200 and me.get("nickname"), "me", (status, me))

    # 3. 팔로우 (rabbit — 시드 팔로우에 없는 대상이면 신규, 있으면 멱등)
    status, follow = call("PUT", "/api/creators/rabbit/follow", {}, token=token)
    expect(status == 200 and follow.get("following") is True, "follow", (status, follow))

    # 4. 피드 → 첫 포스트 좋아요
    status, feed = call("GET", "/api/feed")
    expect(status == 200 and feed.get("items"), "feed", (status,))
    post_id = feed["items"][0]["id"]
    status, like = call("PUT", f"/api/posts/{post_id}/like", {}, token=token)
    expect(status == 200 and like.get("liked") is True and like.get("like_count", 0) >= 1, "like", (status, like))

    # 5. 댓글
    status, comment = call("POST", f"/api/posts/{post_id}/comments", {"body": "저니 스모크 댓글"}, token=token)
    expect(status == 201 and comment.get("body") == "저니 스모크 댓글", "comment", (status, comment))

    # 6. 구독 (첫 티어) — /tiers는 리스트 또는 {items} 양쪽 대응
    def _items(payload: dict | list) -> list:
        return payload if isinstance(payload, list) else payload.get("items", [])

    status, tiers = call("GET", "/api/tiers?creator_id=" + feed["items"][0]["creator_id"])
    if status != 200 or not _items(tiers):
        status, tiers = call("GET", "/api/tiers")
    expect(status == 200 and bool(_items(tiers)), "tiers", (status,))
    tier_id = _items(tiers)[0]["id"]
    status, sub = call("POST", "/api/subscriptions", {"tier_id": tier_id}, token=token)
    expect(status in (201, 422), "subscribe(201 또는 중복 422)", (status, sub))
    status, subs = call("GET", "/api/subscriptions", token=token)
    expect(status == 200 and len(_items(subs)) >= 1, "subscriptions list", (status, subs))

    # 7. 주문 (재고 있는 첫 상품)
    status, products = call("GET", "/api/products")
    expect(status == 200 and products.get("items"), "products", (status,))
    orderable = next(
        (p for p in products["items"] if not p.get("sold_out") and not p.get("locked")),
        None,
    )
    expect(orderable is not None, "orderable product exists")
    status, order = call("POST", "/api/orders", {"product_id": orderable["id"], "qty": 1}, token=token)
    expect(status == 201 and str(order.get("id", "")).startswith("ASN-"), "order create", (status, order))
    order_id = order["id"]
    status, detail = call("GET", f"/api/orders/{order_id}", token=token)
    expect(status == 200 and detail.get("status") == "paid", "order detail", (status, detail))
    status, cancel = call("POST", f"/api/orders/{order_id}/cancel", {}, token=token)
    expect(status == 200 and cancel.get("status") == "cancelled", "order cancel", (status, cancel))

    # 8. 알림 (주문 생성 알림이 최소 1건)
    status, notes = call("GET", "/api/notifications", token=token)
    items = notes.get("items", [])
    expect(status == 200 and len(items) >= 1, "notifications", (status, notes))
    first = items[0]
    status, read = call("POST", f"/api/notifications/{first['id']}/read", {}, token=token)
    expect(status == 200, "notification read", (status, read))
    status, read_all = call("POST", "/api/notifications/read-all", {}, token=token)
    expect(status == 200, "read-all", (status, read_all))

    # 8.5 신고 (안전 채널 — fan-reports, 서버 enum 사유)
    status, report = call(
        "POST",
        "/api/safety/fan-reports",
        {"report_type": "other", "narrative": "저니 스모크 신고 — 데모 접수 확인"},
        token=token,
    )
    expect(status == 201, "fan report", (status, report))

    # 9. 로그아웃 → me 401
    status, _ = call("POST", "/api/fan/logout", {}, token=token)
    expect(status == 200, "logout", (status,))
    status, _ = call("GET", "/api/fan/me", token=token)
    expect(status == 401, "me after logout = 401", (status,))

    print("JOURNEY SMOKE: ALL PASS")


if __name__ == "__main__":
    main()
