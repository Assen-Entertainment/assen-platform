#!/usr/bin/env python3
"""신규 프로젝트 'Assen 웹 플랫폼 v1' 생성(addTeams) + ASS-152~199(48 이슈) 프로젝트 편입.
seed_backlog.py의 save_project가 team 키 거부로 실패 → 보정 1회 실행.
"""
import json, urllib.request, urllib.parse, urllib.error, time, os

CRED = os.path.expanduser("~/.claude/.credentials.json")
MCP = "https://mcp.linear.app/mcp"
SUMMARY = ("범용·서브컬쳐 크리에이터-팬 웹 플랫폼. React+Next.js+TS+Tailwind v4+Radix. "
           "DS code-complete(33 컴포넌트+5 화면, 런타임 검증 완료) 위에서 백엔드 연동·화면 확장·"
           "커머스(게이트)·브랜드 확정 진행. 구 메이드/랜딩 백로그 폐기(2026-06-30).")
DESCRIPTION = (
    "## 목적\n범용/서브컬쳐 크리에이터-팬 **웹 플랫폼**. 메이드카페/랜딩 유산을 폐기하고 재편(2026-06-30).\n\n"
    "## 현황(DONE)\n웹 DS code-complete: 33 컴포넌트 + 배럴 + /gallery + 5 화면(Discovery·CreatorProfile·Store·Checkout·WebShell). "
    "런타임 검증 통과(next build exit 0·타입 0오류·9 routes SSG·Playwright 시각 7장).\n\n"
    "## 스택\nReact + Next.js(App Router) + TypeScript + Tailwind v4 + Radix. 모바일=Flutter(ui_kit), 공유=tokens.v2.json + Figma.\n\n"
    "## 소스 문서\nCompany-OS/02_Product/SDLC/08_웹클라이언트_React구현_및_백로그재편_2026-06-30.md (10 에픽 정의).\n\n"
    "## 게이트(승인 필요)\nE5 커머스/결제(PG·IAP·정산) · E6 본인인증 · E7 약관 · E9 브랜드 방향/이름/색 — 대표·법무·PG 결정 전 UI 목업·플래그오프.")


def token():
    d = json.load(open(CRED))
    for k, o in d.get("mcpOAuth", {}).items():
        if k.lower().startswith("linear"):
            if o.get("expiresAt", 0) < time.time() * 1000 + 60000:
                meta = json.load(urllib.request.urlopen(
                    "https://mcp.linear.app/.well-known/oauth-authorization-server", timeout=30))
                body = urllib.parse.urlencode({"grant_type": "refresh_token",
                        "refresh_token": o["refreshToken"], "client_id": o["clientId"]}).encode()
                tok = json.load(urllib.request.urlopen(urllib.request.Request(meta["token_endpoint"],
                        data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=30))
                o["accessToken"] = tok["access_token"]; o["refreshToken"] = tok.get("refresh_token", o["refreshToken"])
                if tok.get("expires_in"): o["expiresAt"] = int((time.time() + tok["expires_in"]) * 1000)
                json.dump(d, open(CRED, "w"))
            return o["accessToken"]
    raise SystemExit("no linear oauth")


AT = token(); SID = [None]


def post(payload):
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
         "Authorization": "Bearer " + AT}
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


post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "assen-fix", "version": "1"}}})
post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

pr = call("save_project", {"name": "Assen 웹 플랫폼 v1", "summary": SUMMARY, "description": DESCRIPTION,
                           "addTeams": ["Assen Entertainment"], "priority": 2, "icon": "Rocket"})
proj = pr.get("project", pr)
pid = proj.get("id")
print("[project] id=%s url=%s" % (pid, proj.get("url") or pr))
if not pid:
    raise SystemExit("project 생성 실패: %s" % pr)

ok = 0; fail = 0
for n in range(152, 200):  # ASS-152 ~ ASS-199 (48건)
    ident = "ASS-%d" % n
    r = call("save_issue", {"id": ident, "project": pid})
    if r.get("_err"):
        fail += 1; print("  FAIL %s %s" % (ident, r["_err"]))
    else:
        ok += 1
        if ok % 12 == 0: print("  ...%d assigned" % ok)
    time.sleep(0.2)
print("=== project assigned %d / 48 (fail %d) ===" % (ok, fail))
