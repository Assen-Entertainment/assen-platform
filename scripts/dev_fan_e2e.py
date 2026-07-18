"""Full FAN consume journey as an API/contract E2E — toolchain-independent (stdlib only).

kakao fan: login -> KYC -> follow `e2ecreator` -> subscribe to its paid tier (mock payment)
-> buy its digital product (mock payment) -> assert both reflect in /subscriptions and
/orders. Complements the browser journeys (e2e/tests/dev-fan-journey.web.spec.ts); this one
proves the same flow at the backend contract level even when the browser toolchain is
unavailable. Run the seed first (scripts/dev_e2e_seed.py). Throttle-tolerant (429 backoff).

    WEB_BASE_URL=https://dev.assenent.com python scripts/dev_fan_e2e.py
"""
from __future__ import annotations
import json, os, socket, time, urllib.error, urllib.parse, urllib.request, uuid
from http.cookiejar import split_header_words

BASE = os.environ.get("WEB_BASE_URL", "https://dev.assenent.com").rstrip("/")
CREATOR = "e2ecreator"
COOKIES: dict[str, str] = {}
FAILS: list[str] = []

try:  # pin the dev subdomain to a live ALB IP if the local resolver is mid-propagation
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
        r.add_header("Origin", BASE)
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


def mreq(method, path, body=None, tries=4, wait=65):
    for i in range(tries):
        st, b = req(method, path, body)
        if st != 429:
            return st, b
        print(f"  429 {method} {path} — wait {wait}s ({i + 1}/{tries})", flush=True)
        time.sleep(wait)
    return 429, None


def check(cond, msg):
    print(("  OK  " if cond else "  FAIL") + " " + msg)
    if not cond:
        FAILS.append(msg)


def main() -> int:
    req("GET", "/api/fan/csrf")
    ru = f"{BASE}/auth/callback/kakao"
    _, sb = req("GET", f"/api/fan/social/kakao/start?{urllib.parse.urlencode({'redirect_uri': ru})}")
    st, _ = req("POST", "/api/fan/social/kakao/callback", {
        "code": "mock-kakao", "state": sb["state"], "redirect_uri": ru,
        "consent_terms": True, "consent_privacy": True, "age_over_14": True, "web": True,
    })
    check(st == 200, f"kakao social login (status={st})")
    _, me = req("GET", "/api/fan/me")
    if isinstance(me, dict) and me.get("kyc_status") != "verified":
        mreq("POST", "/api/fan/verify/start")
        mreq("POST", "/api/fan/verify/confirm")
        _, me = req("GET", "/api/fan/me")
    check(isinstance(me, dict) and me.get("kyc_status") == "verified", "fan is KYC-verified")

    st, creator = req("GET", f"/api/creators/{CREATOR}")
    check(st == 200, f"creator {CREATOR} exists (status={st})")

    st, f = mreq("PUT", f"/api/creators/{CREATOR}/follow")
    check(st in (200, 201) and isinstance(f, dict) and f.get("following") is True, f"follow -> following=true (status={st})")

    _, tiers = req("GET", "/api/tiers")
    tier = next((t for t in (tiers or []) if t.get("creator_id") == creator.get("id")), None)
    check(tier is not None, "creator has a subscribable tier")
    if tier:
        st, _ = mreq("POST", "/api/subscriptions", {"tier_id": tier["id"]})
        check(st in (201, 422), f"subscribe -> 201 (or 422 already-subscribed) (status={st})")

    _, prods = req("GET", "/api/products")
    items = prods.get("items", []) if isinstance(prods, dict) else []
    prod = next((p for p in items if p.get("creator_id") == creator.get("id") and p.get("type") == "digital"), None)
    check(prod is not None, "creator has a sellable digital product")
    order_id = None
    if prod:
        st, order = mreq("POST", "/api/orders", {"product_id": prod["id"], "qty": 1, "idempotency_key": str(uuid.uuid4())})
        check(st == 201 and isinstance(order, dict), f"create order -> 201 (status={st})")
        if isinstance(order, dict):
            order_id = order.get("id")
            check(order.get("status") == "paid", f"order status is paid (mock payment) — got {order.get('status')}")

    _, subs = req("GET", "/api/subscriptions")
    check(isinstance(subs, list) and len(subs) > 0, "active subscription reflected in /subscriptions")
    _, orders = req("GET", "/api/orders")
    oitems = orders.get("items", []) if isinstance(orders, dict) else (orders if isinstance(orders, list) else [])
    check(any(o.get("id") == order_id for o in oitems) if order_id else len(oitems) > 0, "order reflected in /orders")

    print("\n==== FAN E2E: " + ("FAIL — " + "; ".join(FAILS) if FAILS else "PASS") + " ====")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
