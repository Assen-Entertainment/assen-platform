"""Seed deterministic creator content on a deployed stack for the fan E2E to consume.

A mock-google account -> KYC (required before becoming a creator) -> creator `e2ecreator`
-> a SELLING digital product + an ACTIVE paid tier + a published post. Digital, not goods:
demo has shipping_checkout_available=false, so a goods checkout is blocked by design. Writes
are throttled (FAN_WRITE_THROTTLE, per-minute) so mutations back off on 429. Idempotent-ish.

    WEB_BASE_URL=https://dev.assenent.com python scripts/dev_e2e_seed.py
"""
from __future__ import annotations
import json, os, socket, time, urllib.error, urllib.parse, urllib.request
from http.cookiejar import split_header_words

BASE = os.environ.get("WEB_BASE_URL", "https://dev.assenent.com").rstrip("/")
HANDLE = "e2ecreator"
COOKIES: dict[str, str] = {}

# Optional: on a machine whose resolver is mid-propagation for the dev subdomain, pin it to
# a current ALB IP (SNI stays the hostname, so the cert still validates). Best-effort.
try:
    _host = urllib.parse.urlparse(BASE).hostname or ""
    _alb = socket.gethostbyname_ex("assen-dev-api-307204389.ap-northeast-2.elb.amazonaws.com")[2][0]
    _orig = socket.getaddrinfo
    socket.getaddrinfo = lambda h, *a, **k: _orig(_alb if h == _host else h, *a, **k)
except OSError:
    pass


def _store(resp):
    for raw in resp.headers.get_all("Set-Cookie") or []:
        n, v = split_header_words([raw])[0][0]
        if v:
            COOKIES[n] = v


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    if data is not None:
        r.add_header("Content-Type", "application/json")
    if COOKIES:
        r.add_header("Cookie", "; ".join(f"{k}={v}" for k, v in COOKIES.items()))
    if method in ("POST", "PATCH", "PUT", "DELETE"):
        r.add_header("Origin", BASE)  # Django CSRF checks Origin over https
        if "csrftoken" in COOKIES:
            r.add_header("X-CSRFToken", COOKIES["csrftoken"])
    try:
        resp = urllib.request.urlopen(r)
        raw = resp.read().decode()
    except urllib.error.HTTPError as e:
        resp, raw = e, e.read().decode()
    _store(resp)
    try:
        return resp.status, (json.loads(raw) if raw else None)
    except json.JSONDecodeError:
        return resp.status, raw[:160]


def mreq(method, path, body=None, tries=5, wait=65):
    for i in range(tries):
        st, b = req(method, path, body)
        if st != 429:
            return st, b
        print(f"  429 {method} {path} — wait {wait}s ({i + 1}/{tries})", flush=True)
        time.sleep(wait)
    return 429, None


def main() -> int:
    req("GET", "/api/fan/csrf")
    ru = f"{BASE}/auth/callback/google"
    _, sb = req("GET", f"/api/fan/social/google/start?{urllib.parse.urlencode({'redirect_uri': ru})}")
    req("POST", "/api/fan/social/google/callback", {
        "code": "mock-google", "state": sb["state"], "redirect_uri": ru,
        "consent_terms": True, "consent_privacy": True, "age_over_14": True, "web": True,
    })
    _, me = req("GET", "/api/fan/me")
    if isinstance(me, dict) and me.get("kyc_status") != "verified":
        mreq("POST", "/api/fan/verify/start")
        mreq("POST", "/api/fan/verify/confirm")

    if not (isinstance(me, dict) and me.get("handle")):
        # category(버튜버)를 개설 시 지정해 디스커버리 카테고리 필터가 이 시드로 실증되게 한다.
        print("become-creator:", mreq("POST", "/api/studio/profile", {"handle": HANDLE, "name": "E2E Seed Creator", "category": "버튜버"}))
        _, me = req("GET", "/api/fan/me")
    print("handle:", me.get("handle") if isinstance(me, dict) else me)

    st, prod = mreq("POST", "/api/studio/products", {
        "type": "digital", "title": "E2E 디지털 상품", "price": 5000,
        "description": "E2E 시드 디지털 상품", "status": "selling", "pricing_kind": "paid",
    })
    pid = prod.get("id") if isinstance(prod, dict) else None
    print("product:", st, pid)

    st, tier = mreq("POST", "/api/studio/tiers", {
        "name": "E2E 티어", "price": 3000, "benefits": ["독점 콘텐츠", "배지"], "pricing_kind": "paid",
    })
    tid = tier.get("id") if isinstance(tier, dict) else None
    print("tier:", st, tid)

    print("post:", mreq("POST", "/api/posts", {"body": "E2E 시드 포스트\n\n본문입니다.", "is_adult": False})[0])
    print(f"SEED: handle={HANDLE} product_id={pid} tier_id={tid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
