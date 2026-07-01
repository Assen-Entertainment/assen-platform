#!/usr/bin/env python3
"""모바일 에픽(E12) + M1~M10 자식 이슈 생성. 소스=SDLC 10 문서.
실행(WSL): python3 .../tools/linear/seed_mobile.py [--dry]
"""
import json, urllib.request, urllib.parse, urllib.error, time, os, sys

CRED = os.path.expanduser("~/.claude/.credentials.json")
MCP = "https://mcp.linear.app/mcp"
TEAM = "Assen Entertainment"
PROJECT_ID = "fa71d4ac-3cb3-47ef-81d1-c5413d6e513d"
DRY = "--dry" in sys.argv

EPIC = ("[E12] 모바일 구현 (Flutter)", 2,
        "신규 도메인 모바일. 인프라(core_tokens·ui_kit·api_client) 재사용+도메인 신규. 공유 토큰·백엔드 계약. 소스: SDLC 10_모바일_Flutter_아키텍처_및_개발요구사항.")
CHILDREN = [
    ("[M1] 모노레포·토큰 재정비 (Melos 정리 + tokens.v2.json→core_tokens Dart 코드젠 재동기)", 2),
    ("[M2] ui_kit DS 패리티 (웹 DS↔Flutter 위젯: Button·Card·MonetizableItem·PostCard·CreatorThumbCard·MembershipTierCard… + creatorAccent Dart)", 2),
    ("[M3] 앱 기반 (go_router 딥링크·동적 라우트·가드 + BottomNav 셸 + Riverpod 기반)", 2),
    ("[M4] api_client·계약 (B-API OpenAPI→Dart 모델 코드젠 + 인증 인터셉터)", 2),
    ("[M5] 화면 구현 (discovery·creator·feed·search·post·store·membership·mypage·settings·notifications·orders·studio·onboarding)", 2),
    ("[M6] 인증·19+ (소셜 로그인·세션 보안저장·19+ 게이트)", 2),
    ("[M7] 실시간 (챗·알림 WS/FCM)", 3),
    ("[M8][게이트] 커머스/IAP (체크아웃·구독·결제·정산) [승인필요]", 1),
    ("[M9] 품질·배포 (위젯/통합 테스트·CI·스토어 빌드 서명·심사)", 3),
    ("[M10] 메이드 앱/피처 아카이브 (fan_app·operator_app·features 정리)", 3),
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

post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "assen-mobile", "version": "1"}}})
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
    print("   + %s -> %s" % (title[:46], ident or r))
    ok += 1
    time.sleep(0.25)
print("=== epic + %d children ===" % ok)
