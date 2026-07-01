#!/usr/bin/env python3
"""전체 작업 리스트 — 기존 48(에픽+상위) 위에 granular 분해 추가.
부모=기존 식별자(ASS-NNN), 프로젝트=Assen 웹 플랫폼 v1, 상태=Backlog.
실행(WSL): python3 .../tools/linear/seed_v2_breakdown.py [--dry]
"""
import json, urllib.request, urllib.parse, urllib.error, time, os, sys

CRED = os.path.expanduser("~/.claude/.credentials.json")
MCP = "https://mcp.linear.app/mcp"
PROJECT_ID = "fa71d4ac-3cb3-47ef-81d1-c5413d6e513d"  # Assen 웹 플랫폼 v1
DRY = "--dry" in sys.argv

# (parent_identifier, title, priority)
ADD = [
    # E1 기반 보강 (parent=에픽 ASS-152)
    ("ASS-152", "[E1] 환경변수/런타임 설정 분리(.env·config·시크릿 주입)", 2),
    ("ASS-152", "[E1] 전역 error.tsx·loading.tsx·not-found.tsx", 2),
    ("ASS-152", "[E1] SEO 기반 — metadata API·sitemap·robots·OG 이미지", 2),
    ("ASS-152", "[E1] 분석 계측 추상화 레이어(이벤트→수집기)", 3),
    # E2 개별 컴포넌트 (parent=니치 umbrella ASS-160)
    ("ASS-160", "[E2] OTPInput(본인인증/2FA)", 3),
    ("ASS-160", "[E2] StepIndicator(온보딩/체크아웃 단계)", 3),
    ("ASS-160", "[E2] ConsentGroup(약관 동의 묶음)", 3),
    ("ASS-160", "[E2] Select/Combobox(Radix)", 3),
    ("ASS-160", "[E2] Accordion(FAQ/설정)", 3),
    ("ASS-160", "[E2] DatePicker/Calendar", 3),
    ("ASS-160", "[E2] FileUpload/ImageUploader(작성·프로필)", 3),
    ("ASS-160", "[E2] Pagination/무한스크롤 헬퍼", 3),
    ("ASS-160", "[E2] useToast/Toaster 헬퍼(Toast 구동)", 3),
    ("ASS-160", "[E2] RightRail·Breadcrumb(웹 보조 셸)", 3),
    # E3 도메인별 데이터 연동 (parent=데이터연동 umbrella ASS-169)
    ("ASS-169", "[E3] Discovery 데이터 연동(크리에이터/아이템 목록)", 2),
    ("ASS-169", "[E3] Creator 프로필 데이터 연동", 2),
    ("ASS-169", "[E3] Post/피드 데이터 연동(목록·상세·좋아요/댓글)", 2),
    ("ASS-169", "[E3] Store/상품 데이터 연동", 2),
    ("ASS-169", "[E3] Membership/구독 데이터 연동", 2),
    ("ASS-169", "[E3] 검색·알림 데이터 연동", 2),
    # E4 누락 화면 (parent=에픽 ASS-171)
    ("ASS-171", "[E4] 홈/팔로잉 피드 화면", 2),
    ("ASS-171", "[E4] 결제 완료/실패 화면", 2),
    ("ASS-171", "[E4] 주문 내역 화면", 2),
    ("ASS-171", "[E4] 후원/도네이션 플로우", 2),
    ("ASS-171", "[E4] 프로필 편집 화면", 2),
    ("ASS-171", "[E4] 인터랙션 배선 — 좋아요·댓글·공유·팔로우", 2),
    ("ASS-171", "[E4] 안전 — 신고/차단 플로우(팬↔크리에이터)", 2),
    # E4 스튜디오 분해 (parent=스튜디오 umbrella ASS-177)
    ("ASS-177", "[E4] 스튜디오 대시보드(현황·통계)", 2),
    ("ASS-177", "[E4] 스튜디오 콘텐츠 작성/관리", 2),
    ("ASS-177", "[E4] 스튜디오 정산/수익 뷰", 2),
    # E6 인증 갭 (parent=에픽 ASS-182)
    ("ASS-182", "[E6] 비밀번호 재설정/찾기", 2),
    ("ASS-182", "[E6] 이메일 인증", 3),
    # E10 운영 갭 (parent=에픽 ASS-197)
    ("ASS-197", "[E10] 에러 트래킹/모니터링(Sentry 등)", 3),
    ("ASS-197", "[E10] 환경 분리(dev/stg/prod) + 시크릿 관리", 3),
]


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


print("=== seed v2 분해 %d건 %s ===" % (len(ADD), "[DRY]" if DRY else ""))
if DRY:
    for p, t, pr in ADD: print("  %s <- %s (P%d)" % (p, t, pr))
    raise SystemExit(0)

post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "assen-seed2", "version": "1"}}})
post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

ok = 0; fail = 0
for parent, title, prio in ADD:
    r = call("save_issue", {"title": title, "team": "Assen Entertainment", "state": "Backlog",
                            "priority": prio, "project": PROJECT_ID, "parentId": parent})
    cand = r.get("issue", r) if isinstance(r, dict) else {}
    if r.get("_err"):
        fail += 1; print("  FAIL %s %s" % (title[:40], r["_err"]))
    else:
        ok += 1; print("  + %s -> %s" % (title[:46], cand.get("identifier") or cand.get("url")))
    time.sleep(0.25)
print("=== 추가 %d / %d (fail %d) ===" % (ok, len(ADD), fail))
