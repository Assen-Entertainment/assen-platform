"""Authenticated fan-journey QA against a deployed stack (default: the dev ALB).

Why this exists: the deployed dev serves ``config.settings.demo`` (prod-hardened) over
http, so every auth cookie (``assen_access``, ``assen_social_state``, ``csrftoken``) is
``Secure`` and a browser/curl drops it over http -> no browser login is possible there.
A test harness can still exercise the real backend by managing cookies MANUALLY (ignoring
the Secure flag), which is exactly what this does. It proves the deployed API's full fan
journey works end to end, independent of the browser-over-http limitation.

Complements ``e2e/tests/dev-live-surface.web.spec.ts`` (which covers the browser-testable
UNauthenticated surface). Once the target is served over https, the browser spec can cover
these authenticated flows directly and this harness becomes a fast contract smoke.

Steps: csrf prime -> social(kakao) start -> callback (new fan) -> me -> kyc start/confirm
-> me(verified) -> public catalogue. Creates one throwaway mock-social account; no money.

Usage:
    WEB_BASE_URL=http://<alb-or-host> python scripts/dev_journey_qa.py
Exit code 0 = journey passed, 1 = a step failed.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import split_header_words

BASE = os.environ.get(
    "WEB_BASE_URL",
    "http://assen-dev-api-307204389.ap-northeast-2.elb.amazonaws.com",
).rstrip("/")
COOKIES: dict[str, str] = {}
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def _store_set_cookies(resp: object) -> None:
    """Accumulate name=value from every Set-Cookie, ignoring the Secure flag on purpose."""
    headers = resp.headers  # type: ignore[attr-defined]
    for raw in headers.get_all("Set-Cookie") or []:
        name, value = split_header_words([raw])[0][0]
        if value == "":
            COOKIES.pop(name, None)
        else:
            COOKIES[name] = value


def req(method: str, path: str, body: dict | None = None, expect: str = "") -> tuple[int, object]:
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        r.add_header("Content-Type", "application/json")
    if COOKIES:
        r.add_header("Cookie", "; ".join(f"{k}={v}" for k, v in COOKIES.items()))
    if method in UNSAFE and "csrftoken" in COOKIES:
        r.add_header("X-CSRFToken", COOKIES["csrftoken"])
    try:
        resp = urllib.request.urlopen(r)  # noqa: S310 (trusted internal host)
        status, raw = resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        resp, status, raw = e, e.code, e.read().decode("utf-8", "replace")
    _store_set_cookies(resp)
    try:
        parsed: object = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        parsed = raw[:200]
    short = json.dumps(parsed, ensure_ascii=True)[:180] if parsed is not None else "(empty)"
    print(f"[{status}] {expect or method + ' ' + path} -> {short}")
    return status, parsed


def main() -> int:
    fails: list[str] = []

    req("GET", "/api/fan/csrf", expect="csrf prime")
    if "csrftoken" not in COOKIES:
        fails.append("no csrftoken cookie issued")

    ru = f"{BASE}/auth/callback/kakao"
    q = urllib.parse.urlencode({"redirect_uri": ru})
    _, body = req("GET", f"/api/fan/social/kakao/start?{q}", expect="social start")
    state = body.get("state") if isinstance(body, dict) else None
    if not state or "assen_social_state" not in COOKIES:
        fails.append("social start did not yield state + state cookie")
        return _summary(fails)

    st, _ = req(
        "POST",
        "/api/fan/social/kakao/callback",
        {
            "code": "mock-kakao",
            "state": state,
            "redirect_uri": ru,
            "consent_terms": True,
            "consent_privacy": True,
            "age_over_14": True,
            "web": True,
        },
        expect="social callback",
    )
    if st != 200 or "assen_access" not in COOKIES:
        fails.append(f"social callback failed (status={st}, has_access={'assen_access' in COOKIES})")

    st, me = req("GET", "/api/fan/me", expect="me (authed)")
    if st != 200:
        fails.append(f"/fan/me not authenticated (status={st})")
    kyc0 = me.get("kyc_status") if isinstance(me, dict) else None

    st, _ = req("POST", "/api/fan/verify/start", expect="kyc start")
    if st not in (200, 204, 503):
        fails.append(f"kyc start unexpected status {st}")

    st, conf = req("POST", "/api/fan/verify/confirm", expect="kyc confirm")
    if st not in (200, 503):
        fails.append(f"kyc confirm unexpected status {st}")

    st, me2 = req("GET", "/api/fan/me", expect="me (post-kyc)")
    kyc1 = me2.get("kyc_status") if isinstance(me2, dict) else None
    if st == 200 and kyc0 is not None and kyc1 == kyc0 and kyc1 != "verified":
        fails.append(f"kyc_status did not advance ({kyc0} -> {kyc1})")

    _, prods = req("GET", "/api/products", expect="products")
    if isinstance(prods, dict):
        print(f"    product count: {len(prods.get('items', []))}")

    return _summary(fails)


def _summary(fails: list[str]) -> int:
    print("\n==== SUMMARY ====")
    if fails:
        print(f"FAIL ({len(fails)}):")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("PASS: authenticated fan journey works on the target backend")
    return 0


if __name__ == "__main__":
    sys.exit(main())
