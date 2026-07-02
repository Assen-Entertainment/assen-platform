#!/usr/bin/env python3
"""백엔드 에픽(E11) + B1~B9 자식 이슈 생성. 소스=SDLC 09 문서.
실행(WSL): python3 .../tools/linear/seed_backend.py [--dry]
"""
import json, urllib.request, urllib.parse, urllib.error, time, os, sys

CRED = os.path.expanduser("~/.claude/.credentials.json")
MCP = "https://mcp.linear.app/mcp"
TEAM = "Assen Entertainment"
PROJECT_ID = "fa71d4ac-3cb3-47ef-81d1-c5413d6e513d"  # Assen 웹 플랫폼 v1
DRY = "--dry" in sys.argv

EPIC = ("[E11] 백엔드 구현 (Django Ninja 모듈러 모놀리스)", 2,
        "신규 도메인 백엔드. 인프라 재사용+도메인 신규. 실시간 additive·추출형 MSA. 소스: SDLC 09_백엔드_아키텍처_및_개발요구사항.")
CHILDREN = [
    ("[B1] 도메인 모델·마이그레이션 (Creator·Follow·Post·Comment·Like·Product·Order·MembershipTier·Subscription)", 2),
    ("[B2] 핵심 읽기 API (creators·posts·feed·products·tiers·search — 커서 페이지네이션·OpenAPI)", 2),
    ("[B3] 인증·인가 (identity 재사용·opaque+refresh 회전·소셜·RBAC·19+ 미들웨어)", 2),
    ("[B4] 쓰기 뮤테이션 (follow 토글·like·comment·order 목·subscription 목)", 2),
    ("[B5] 프론트 연동 (lib/api mock→실 API·openapi-typescript 타입생성·React Query 연결)", 2),
    ("[B6] 실시간 (Channels+Redis: 챗·알림·프레즌스 / 라이브=미디어 프로바이더 토큰)", 3),
    ("[B7][게이트] 커머스/정산·결제 (주문 상태머신·정산 Celery·PG 연동) [승인필요]", 1),
    ("[B8] 품질·운영 (pytest·CI typecheck/lint/test·Sentry·로깅·메트릭·배포)", 3),
    ("[B9] 메이드 앱 아카이브·정리 (cast·cheki·reservation 등) + 경계 리팩토링", 3),
]


def token():
    d = json.load(open(CRED))
    for k, o in d.get("mcpOAuth", {}).items():
        if k.lower().startswith("linear"):
            if o.get("expiresAt", 0) < time.time() * 1000 + 60000:
                meta = json.load(urllib.request.urlopen("https://mcp.linear.app/.well-known/oauth-authorization-server", timeout=30))
                body = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": o["refreshToken"], "client_id": o["clientId"]}).encode()
                tok = json.load(urllib.request.urlopen(urllib.request.Request(meta["token_endpoint"], data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=30))
                o["accessToken"] = tok["access_token"]; o["refreshToken"] = tok.get("refresh_token", o["refreshToken"])
                if tok.get("expires_in"): o["expiresAt"] = int((time.time() + tok["expires_in"]) * 1000)
                json.dump(d, open(CRED, "w"))
            return o["accessToken"]
    raise SystemExit("no linear oauth")


AT = token(); SID = [None]


def post(payload):
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "Authorization": "Bearer " + AT}
    if SID[0]: h["Mcp-Session-Id"] = SID[0]
    r = urllib.request.urlopen(urllib.request.Request(MCP, data=json.dumps(payload).encode(), headers=h), timeout=120)
    if r.headers.get("Mcp-Session-Id"): SID[0] = r.headers.get("Mcp-Session-Id")
    raw = r.read().decode()
    if "text/event-stream" in r.headers.get("Content-Type", ""):
        out = None
        for ln in raw.splitlines():
            if ln.startswith("data:"):
                try: out = json.loads(ln[5:].strip())
                except Exception: pass
        return out
    return json.loads(raw) if raw.strip() else None


def call(name, args):
    r = post({"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": name, "arguments": args}})
    res = r.get("result", r)
    txt = "".join(c.get("text", "") for c in res.get("content", [])) if isinstance(res, dict) else ""
    try: return json.loads(txt)
    except Exception: return {"_raw": txt, "_err": r.get("error")}


def find_id(o):
    if not isinstance(o, dict): return None, None
    c = o.get("issue") or o
    return c.get("id"), c.get("identifier") or c.get("url")


if DRY:
    print("EPIC:", EPIC[0]); [print("  ", t) for t, _ in CHILDREN]; raise SystemExit(0)

post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "assen-be", "version": "1"}}})
post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

er = call("save_issue", {"title": EPIC[0], "team": TEAM, "state": "Backlog", "priority": EPIC[1], "project": PROJECT_ID, "description": EPIC[2]})
eid, eident = find_id(er)
print("[epic] %s -> %s (%s)" % (EPIC[0], eident, eid))
ok = 0
for title, prio in CHILDREN:
    a = {"title": title, "team": TEAM, "state": "Backlog", "priority": prio, "project": PROJECT_ID}
    if eid: a["parentId"] = eid
    r = call("save_issue", a)
    _, ident = find_id(r)
    print("   + %s -> %s" % (title[:48], ident or r))
    ok += 1
    time.sleep(0.25)
print("=== epic + %d children ===" % ok)
