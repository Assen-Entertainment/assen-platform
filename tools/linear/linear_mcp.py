#!/usr/bin/env python3
"""Assen Linear bridge — WSL의 Linear MCP OAuth(mcp.linear.app/mcp)를 재사용해 호출.
실행(WSL): python3 /mnt/c/Users/daisy/Assen/assen-platform/tools/linear/linear_mcp.py <cmd>
  tools                      # 툴 목록
  schema <name...>           # 입력 스키마(properties)
  call <tool> '<json args>'  # tools/call 실행 → 텍스트 결과 출력
토큰 만료 시 refreshToken으로 자동 갱신 후 ~/.claude/.credentials.json 갱신(백업 .bak).
"""
import json, urllib.request, urllib.parse, urllib.error, sys, time, shutil, os

CRED = os.path.expanduser("~/.claude/.credentials.json")
MCP = "https://mcp.linear.app/mcp"


def load():
    d = json.load(open(CRED))
    mo = d.get("mcpOAuth", {})
    for k in mo:
        if k.lower().startswith("linear"):
            return d, k, mo[k]
    raise SystemExit("[bridge] no linear oauth in credentials")


def token():
    d, k, o = load()
    exp = o.get("expiresAt", 0)
    if exp and exp < time.time() * 1000 + 60000:  # 만료/만료임박
        meta = json.load(urllib.request.urlopen(
            "https://mcp.linear.app/.well-known/oauth-authorization-server", timeout=30))
        body = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": o["refreshToken"],
            "client_id": o["clientId"],
        }).encode()
        tok = json.load(urllib.request.urlopen(urllib.request.Request(
            meta["token_endpoint"], data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=30))
        o["accessToken"] = tok["access_token"]
        o["refreshToken"] = tok.get("refresh_token", o["refreshToken"])
        if tok.get("expires_in"):
            o["expiresAt"] = int((time.time() + tok["expires_in"]) * 1000)
        shutil.copy(CRED, CRED + ".bak")
        json.dump(d, open(CRED, "w"))
        sys.stderr.write("[bridge] token refreshed\n")
    return o["accessToken"]


AT = token()
SID = [None]


def post(payload):
    h = {"Content-Type": "application/json",
         "Accept": "application/json, text/event-stream",
         "Authorization": "Bearer " + AT}
    if SID[0]:
        h["Mcp-Session-Id"] = SID[0]
    req = urllib.request.Request(MCP, data=json.dumps(payload).encode(), headers=h)
    try:
        r = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as e:
        sys.stderr.write("HTTP %d %s\n" % (e.code, e.read().decode()[:800]))
        raise
    if r.headers.get("Mcp-Session-Id"):
        SID[0] = r.headers.get("Mcp-Session-Id")
    raw = r.read().decode()
    if "text/event-stream" in r.headers.get("Content-Type", ""):
        out = None
        for ln in raw.splitlines():
            if ln.startswith("data:"):
                try:
                    out = json.loads(ln[5:].strip())
                except Exception:
                    pass
        return out
    return json.loads(raw) if raw.strip() else None


def rpc(method, params, i=1):
    return post({"jsonrpc": "2.0", "id": i, "method": method, "params": params})


rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                   "clientInfo": {"name": "assen-bridge", "version": "1"}})
post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

cmd = sys.argv[1] if len(sys.argv) > 1 else "tools"
if cmd == "tools":
    for t in rpc("tools/list", {}, 2)["result"]["tools"]:
        print(t["name"], "::", (t.get("description") or "").replace("\n", " ")[:70])
elif cmd == "schema":
    want = set(sys.argv[2:])
    for t in rpc("tools/list", {}, 2)["result"]["tools"]:
        if t["name"] in want:
            print("###", t["name"])
            print(json.dumps(t.get("inputSchema", {}).get("properties", {}))[:1800])
elif cmd == "call":
    args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    r = rpc("tools/call", {"name": sys.argv[2], "arguments": args}, 3)
    res = r.get("result", r)
    if isinstance(res, dict) and "content" in res:
        for c in res["content"]:
            if c.get("type") == "text":
                print(c["text"])
    else:
        print(json.dumps(r))
elif cmd == "issues":
    # 전 이슈 페이지네이션 compact: identifier \t state \t id \t title
    team = sys.argv[2] if len(sys.argv) > 2 else None
    cursor = None
    n = 0
    while True:
        a = {"limit": 250}
        if team:
            a["team"] = team
        if cursor:
            a["cursor"] = cursor
        r = rpc("tools/call", {"name": "list_issues", "arguments": a}, 3)
        txt = next(c["text"] for c in r["result"]["content"] if c.get("type") == "text")
        data = json.loads(txt)
        items = data.get("issues") or data.get("nodes") or []
        for it in items:
            st = it.get("state")
            stn = st.get("name") if isinstance(st, dict) else st
            print("%s\t%s\t%s\t%s" % (it.get("identifier"), stn, it.get("id"), (it.get("title") or "")[:70]))
            n += 1
        cursor = data.get("endCursor") or data.get("cursor")
        if not (data.get("hasNextPage") and cursor):
            break
    sys.stderr.write("TOTAL %d\n" % n)
