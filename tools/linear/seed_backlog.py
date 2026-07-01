#!/usr/bin/env python3
"""Assen 신규 웹 백로그 시드 — 프로젝트 + 10 에픽(부모이슈) + 자식이슈 일괄 생성.
실행(WSL): python3 .../tools/linear/seed_backlog.py [--dry]
  --dry  실제 생성 없이 계획만 출력.
기존 백로그 삭제 후 1회 실행. (재실행 시 중복 생성됨 — 주의)
SDLC 소스: Company-OS/02_Product/SDLC/08_웹클라이언트_React구현_및_백로그재편_2026-06-30.md
"""
import json, urllib.request, urllib.parse, urllib.error, sys, time, os

CRED = os.path.expanduser("~/.claude/.credentials.json")
MCP = "https://mcp.linear.app/mcp"
TEAM = "Assen Entertainment"
PROJECT_NAME = "Assen 웹 플랫폼 v1"
PROJECT_SUMMARY = ("범용/서브컬쳐 크리에이터-팬 웹 플랫폼. React+Next.js+TS+Tailwind v4+Radix. "
                   "DS code-complete(33 컴포넌트+5 화면, 런타임 검증 완료) 위에서 백엔드 연동·화면 확장·"
                   "커머스(게이트)·브랜드 확정을 진행. 구 메이드카페/랜딩 백로그는 전면 폐기(2026-06-30).")
DRY = "--dry" in sys.argv

EPICS = [
    ("E1", "웹 기반 확정 & CI", 2, [
        "스캐폴드 정식화(package.json·tsconfig·next.config·postcss·app/layout·page 커밋)",
        "ESLint flat config + jsx-a11y + 빌드 게이트(ignoreDuringBuilds 해제)",
        "CI: typecheck + build + lint (GitHub Actions)",
        "토큰 파이프라인 단일화(web build-tokens ↔ tools/tokens, tokens.v2.json 단일소스)",
        "Pretendard 번들(next/font/local) + 폴백 제거",
        "컴포넌트 갤러리 발행(/gallery → Storybook/정적 호스팅)",
    ]),
    ("E2", "DS 보강", 3, [
        "니치 컴포넌트(OTPInput·StepIndicator·ConsentGroup·RightRail·Breadcrumb·Pagination·FileUpload)",
        "오버레이 enter/exit 모션(tw-animate-css)",
        "forwardRef 스윕 잔여(Spinner·Skeleton·Divider·PriceLabel)",
        "Button filled hover 색조 시프트 토큰(Stripe식, opacity 대체)",
        "갤러리 커버리지(Sheet·Toast·셸 시연 추가)",
        "a11y 자동 테스트(토큰 대비 자동검증 + axe)",
    ]),
    ("E3", "백엔드 연동 (Django 재사용)", 2, [
        "API 클라이언트 + 인증 토큰 배선(opaque + refresh 회전)",
        "서버상태 라이브러리 도입(React Query 등)",
        "데이터 연동: Discovery·Creator·Post·Store·Membership (mock→API)",
        "데이터 이벤트 스키마 클라이언트 계측",
    ]),
    ("E4", "화면 확장", 2, [
        "마이페이지 / 설정 / 계정",
        "온보딩(가입 후 관심 크리에이터 선택)",
        "검색 결과 / 필터",
        "알림 센터(허용 알림 정책 반영)",
        "포스트 상세 / 작성 에디터",
        "크리에이터 스튜디오(대시보드·콘텐츠 작성·정산 뷰)",
    ]),
    ("E5", "커머스/결제 [게이트]", 1, [
        "[게이트] 실결제 PG 연동(웹) — 계약 선행 [승인필요]",
        "[게이트] 모바일 IAP 트랙 [승인필요]",
        "[게이트] 정산 구조 구현 [승인필요]",
    ]),
    ("E6", "인증/본인인증 [게이트]", 2, [
        "소셜 로그인 + 세션",
        "[게이트] 본인인증(성인 게이팅 전제) [승인필요]",
    ]),
    ("E7", "컴플라이언스", 2, [
        "19+ 연령 게이팅 UI + 정책 적용",
        "[게이트] 약관/개인정보 동의 플로우",
    ]),
    ("E8", "모바일(Flutter) 정합", 3, [
        "tokens.v2.json 단일소스 → Dart 코드젠 재동기",
        "creatorAccent Dart ↔ TS 패리티 유지",
        "기존 ui_kit ↔ 웹 IA 정합",
    ]),
    ("E9", "브랜드 확정 [게이트: 서브컬쳐 회의]", 2, [
        "[게이트] 브랜드 방향 확정(서브컬쳐 vs 순수 범용) → 루브릭 step2",
        "시그니처 강화(루브릭 §6: 딜라이트 warmth·시그니처 발현)",
        "[게이트] 이름 변경 검토(Assen 탈피 신호)",
        "[게이트] 브랜드색 확정(Assen Indigo 가역)",
    ]),
    ("E10", "배포/인프라", 3, [
        "웹 호스팅 결정(Vercel vs ECS Fargate) + 배포 하네스",
        "도메인 / SSL / 환경 분리",
    ]),
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
    txt = ""
    if isinstance(res, dict) and "content" in res:
        txt = "".join(c.get("text", "") for c in res["content"] if c.get("type") == "text")
    try:
        return json.loads(txt)
    except Exception:
        return {"_raw": txt}


def find_id(obj):
    """반환 객체에서 issue/project id·identifier 추출(방어적)."""
    if not isinstance(obj, dict): return None, None
    cand = obj.get("issue") or obj.get("project") or obj
    return cand.get("id"), cand.get("identifier") or cand.get("url")


post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "assen-seed", "version": "1"}}})
post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

print("=== Assen 웹 백로그 시드 %s ===" % ("(DRY)" if DRY else "(LIVE)"))
# 1) project
proj_id = None
if DRY:
    print("[project] %s" % PROJECT_NAME)
else:
    pr = call("save_project", {"name": PROJECT_NAME, "summary": PROJECT_SUMMARY, "team": TEAM})
    proj_id, _ = find_id(pr)
    print("[project] %s -> %s" % (PROJECT_NAME, proj_id or pr))

total = 0
for key, title, prio, children in EPICS:
    etitle = "[%s] %s" % (key, title)
    if DRY:
        print("  [epic] %s (P%d) +%d children" % (etitle, prio, len(children)))
        total += 1 + len(children)
        continue
    args = {"title": etitle, "team": TEAM, "state": "Backlog", "priority": prio,
            "description": "에픽 %s. SDLC 08 문서 §3 참조. 자식 이슈로 분할." % key}
    if proj_id: args["project"] = proj_id
    er = call("save_issue", args)
    eid, eident = find_id(er)
    print("  [epic] %s -> %s (%s)" % (etitle, eident, eid))
    total += 1
    if not eid:
        print("    ! epic id 미확보 — 자식 parentId 생략", er);
    for ch in children:
        cargs = {"title": "[%s] %s" % (key, ch), "team": TEAM, "state": "Backlog", "priority": prio}
        if proj_id: cargs["project"] = proj_id
        if eid: cargs["parentId"] = eid
        cr = call("save_issue", cargs)
        cid, cident = find_id(cr)
        print("      - %s -> %s" % (ch[:50], cident or cid or cr))
        total += 1
        time.sleep(0.25)
    time.sleep(0.25)

print("=== 생성 총 %d개 (에픽10 + 자식%d) ===" % (total, total - 10))
