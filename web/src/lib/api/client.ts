import { config } from "@/lib/config";

/** API 오류 — status + 서버 detail 보존. */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    /**
     * 비정상 응답 본문 `{detail}` 문자열(있을 때). 사용자 안내 분기에 사용.
     * ※문자열 결합/부분일치로 분기하는 소비처는 취약 — 서버 error code 도입 시 교체(백로그).
     */
    public detail?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface ApiOptions extends RequestInit {
  token?: string;
}

/** 쿠키 인증 시 CSRF double-submit이 필요 없는 안전 메서드. */
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS", "TRACE"]);

/**
 * 요청 base URL 결정.
 * - 브라우저: `config.apiUrl`(프록시 모드에선 `/api` 같은 상대 경로 — 동일 오리진).
 * - 서버(SSR): 절대 URL이 필요 → `API_INTERNAL_URL`(서버 전용) 우선, 없으면 apiUrl 폴백.
 */
function baseUrl(isServer: boolean): string {
  if (isServer) return process.env.API_INTERNAL_URL || config.apiUrl;
  return config.apiUrl;
}

/** 브라우저 쿠키에서 값 추출(비-httpOnly csrftoken 읽기용). */
function readBrowserCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : undefined;
}

/** 비정상 응답 본문에서 `{detail}` 문자열만 안전 추출(비-JSON·비객체·비문자열은 undefined). */
async function parseErrorDetail(res: Response): Promise<string | undefined> {
  try {
    const text = await res.text();
    if (!text) return undefined;
    const data: unknown = JSON.parse(text);
    if (data && typeof data === "object" && "detail" in data) {
      const d = (data as { detail?: unknown }).detail;
      return typeof d === "string" ? d : undefined;
    }
  } catch {
    /* 비-JSON 본문 등은 detail 없음 */
  }
  return undefined;
}

let csrfPriming: Promise<void> | null = null;
/**
 * csrftoken 쿠키 확보 — 없으면 `GET /fan/csrf`로 프라이밍. 동시 요청은 in-flight
 * promise를 공유하고, 프라이밍이 끝나면 promise를 리셋해 (여전히 쿠키가 없으면) 다음
 * unsafe 요청이 재시도할 수 있게 한다(모듈 플래그의 "1회 실패 후 영구 차단" 버그 회피).
 */
async function ensureCsrfToken(base: string): Promise<string | undefined> {
  let token = readBrowserCookie("csrftoken");
  if (!token) {
    if (!csrfPriming) {
      csrfPriming = fetch(`${base}/fan/csrf`, { credentials: "include" }).then(
        () => undefined,
      );
      void csrfPriming.finally(() => {
        csrfPriming = null;
      });
    }
    try {
      await csrfPriming;
    } catch {
      /* 프라이밍 실패는 무시 — 서버가 403으로 응답하면 호출측이 처리 */
    }
    token = readBrowserCookie("csrftoken");
  }
  return token;
}

let refreshInFlight: Promise<boolean> | null = null;
/**
 * 401 회복(브라우저 전용) — `POST /fan/refresh`로 액세스 쿠키 재발급을 1회 시도한다.
 * 동시 401은 in-flight refresh promise를 공유(중복 refresh 방지). 성공(2xx)이면 true(원
 * 요청 재시도 가능), 실패면 false(401 그대로 전파 → SessionGuard). raw fetch로 호출하므로
 * refresh 자체가 401이어도 재귀하지 않는다.
 */
function refreshSession(base: string): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const csrf = readBrowserCookie("csrftoken");
      const res = await fetch(`${base}/fan/refresh`, {
        method: "POST",
        credentials: "include",
        // 빈 바디는 ninja 필수 스키마 검증에서 422가 되므로 `{}`를 보낸다(토큰 부재=401 의미 유지).
        headers: { "Content-Type": "application/json", ...(csrf ? { "X-CSRFToken": csrf } : {}) },
        body: "{}",
      }).catch(() => null);
      return Boolean(res && res.ok);
    })();
    void refreshInFlight.finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

/** SSR 요청에 브라우저 쿠키를 포워딩(next/headers는 동적 import — 클라 번들 오염 방지). */
async function serverCookieHeader(): Promise<string | undefined> {
  try {
    const { cookies } = await import("next/headers");
    const store = await cookies();
    const pairs = store.getAll().map((c) => `${c.name}=${c.value}`);
    return pairs.length ? pairs.join("; ") : undefined;
  } catch (e) {
    // Next 정적 프리렌더에서 cookies()는 "동적 사용" 신호를 던진다 — 삼키지 말고 전파해
    // 해당 페이지를 동적 렌더로 전환시킨다(라이브 빌드에서 백엔드 호출 전 bailout).
    if (e && typeof e === "object" && "digest" in e && String((e as { digest?: string }).digest).includes("DYNAMIC_SERVER_USAGE")) {
      throw e;
    }
    // 그 외(요청 스코프 밖 등)는 쿠키 없이 진행.
    return undefined;
  }
}

/**
 * 타입드 fetch 래퍼. 쿠키 세션(`credentials:"include"`) + 불안전 메서드 CSRF echo +
 * SSR 쿠키 포워딩 + 401 refresh-and-retry를 처리한다. 비정상 응답은 status와 서버 detail을
 * 보존한 ApiError로 노출(호출측 처리).
 */
export async function apiFetch<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const { token, headers, method, ...rest } = opts;
  const isServer = typeof window === "undefined";
  const base = baseUrl(isServer);
  const verb = (method ?? "GET").toUpperCase();

  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(headers as Record<string, string> | undefined),
  };

  // 불안전 메서드(POST/PUT/DELETE/PATCH) → CSRF double-submit 헤더(쿠키 인증, 브라우저 전용).
  if (!isServer && !SAFE_METHODS.has(verb)) {
    const csrf = await ensureCsrfToken(base);
    if (csrf) finalHeaders["X-CSRFToken"] = csrf;
  }

  // SSR → 브라우저 세션 쿠키를 그대로 전달(orders/subscriptions/notifications 인증 통로).
  if (isServer) {
    const cookieHeader = await serverCookieHeader();
    if (cookieHeader) finalHeaders["Cookie"] = cookieHeader;
  }

  const requestInit: RequestInit = {
    ...rest,
    method,
    credentials: "include",
    headers: finalHeaders,
  };
  // SSR 인증 요청은 라우트/데이터 캐시에 절대 담지 않는다 — 쿠키별 응답이 공유 캐시로
  // 새어 다른 세션에 혼입되는 것을 원천 차단(방어심층).
  if (isServer) requestInit.cache = "no-store";

  let res = await fetch(`${base}${path}`, requestInit);

  // 401 회복(브라우저 전용) — refresh 엔드포인트 자체가 아니면 1회 refresh 후 원 요청 재시도.
  // refresh도 401이면(refreshed=false) 원 401을 그대로 전파해 SessionGuard가 처리한다.
  if (res.status === 401 && !isServer && path !== "/fan/refresh") {
    const refreshed = await refreshSession(base);
    if (refreshed) {
      // refresh 과정에서 csrftoken 쿠키가 회전됐을 수 있어 unsafe 메서드는 헤더를 재확보.
      if (!SAFE_METHODS.has(verb)) {
        const csrf = readBrowserCookie("csrftoken");
        if (csrf) finalHeaders["X-CSRFToken"] = csrf;
      }
      res = await fetch(`${base}${path}`, requestInit);
    }
  }

  if (!res.ok) {
    const detail = await parseErrorDetail(res);
    throw new ApiError(res.status, `API ${res.status}: ${path}`, detail);
  }
  if (res.status === 204) return undefined as T;
  // logout/csrf 등 일부 200 응답은 본문이 비어 있음 → 안전 파싱.
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}
