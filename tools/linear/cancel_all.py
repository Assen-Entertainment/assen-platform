#!/usr/bin/env python3
"""기존 Linear 이슈 전체를 Canceled 상태로 전환(소프트 삭제) — 하드삭제 툴 부재 대응.
실행(WSL): python3 .../tools/linear/cancel_all.py [--dry]
주의: 팀의 모든 비-Canceled 이슈를 Canceled로. 방향 전환에 따른 백로그 폐기용(2026-06-30).
영구 삭제는 Linear UI(Canceled 필터→전체선택→Delete)로.
"""
import json, urllib.request, urllib.parse, urllib.error, sys, time, os

CRED = os.path.expanduser("~/.claude/.credentials.json")
MCP = "https://mcp.linear.app/mcp"
DRY = "--dry" in sys.argv


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
      "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "assen-cancel", "version": "1"}}})
post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

# collect all non-canceled issues
todo = []
cursor = None
while True:
    a = {"limit": 250}
    if cursor: a["cursor"] = cursor
    data = call("list_issues", a)
    items = data.get("issues") or data.get("nodes") or []
    for it in items:
        st = it.get("state")
        stn = st.get("name") if isinstance(st, dict) else st
        if stn != "Canceled":
            todo.append((it.get("identifier"), it.get("id")))
    cursor = data.get("endCursor") or data.get("cursor")
    if not (data.get("hasNextPage") and cursor):
        break

print("대상(비-Canceled) %d건%s" % (len(todo), " [DRY]" if DRY else ""))
if DRY:
    for ident, _ in todo: print("  would cancel", ident)
    raise SystemExit(0)

ok = 0; fail = 0
for ident, iid in todo:
    try:
        r = call("save_issue", {"id": iid, "state": "Canceled"})
        if r.get("_err"):
            fail += 1; print("  FAIL", ident, r.get("_err"))
        else:
            ok += 1
            if ok % 20 == 0: print("  ...%d canceled" % ok)
    except Exception as e:
        fail += 1; print("  EXC", ident, str(e)[:80])
    time.sleep(0.2)
print("=== canceled %d, fail %d ===" % (ok, fail))
