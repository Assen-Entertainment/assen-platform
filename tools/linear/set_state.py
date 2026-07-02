#!/usr/bin/env python3
"""이슈 상태 일괄 변경 — autopilot 진행 추적용.
실행(WSL): python3 .../tools/linear/set_state.py "<State>" ASS-NNN [ASS-NNN ...]
State: Backlog | Todo | "In Progress" | "In Review" | Done | Canceled
"""
import json, urllib.request, urllib.parse, urllib.error, time, os, sys

CRED = os.path.expanduser("~/.claude/.credentials.json")
MCP = "https://mcp.linear.app/mcp"


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
      "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "assen-state", "version": "1"}}})
post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

state = sys.argv[1]
for ident in sys.argv[2:]:
    r = call("save_issue", {"id": ident, "state": state})
    print("%s -> %s : %s" % (ident, state, "ok" if not r.get("_err") else r["_err"]))
    time.sleep(0.2)
