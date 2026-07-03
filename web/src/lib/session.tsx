"use client";
// 세션 — 이중 경로.
//  • USE_API(config.apiUrl 설정): 실 인증. React Query ['auth','me']로 /fan/me를 소비하고
//    OTP 로그인/가입/로그아웃을 실 엔드포인트로 수행한다. 쿠키(httpOnly assen_access)는
//    브라우저가 credentials:"include"로 송신하므로 토큰을 저장하지 않는다.
//  • USE_API=false(빌드/CI/오프라인·테스트): 기존 localStorage mock 유저(실 인증 아님).
//    실 크리덴셜/토큰은 어느 경로에서도 저장하지 않는다.
import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { config } from "@/lib/config";
import { apiFetch, ApiError } from "@/lib/api/client";

const USE_API = Boolean(config.apiUrl);

export interface SessionUser {
  id: string;
  name: string;
  handle: string;
  role: "fan" | "creator";
  avatarUrl?: string;
}

/** OTP 가입 입력. */
export interface SignupInput {
  phone: string;
  otp: string;
  nickname: string;
  consentTerms: boolean;
  consentPrivacy: boolean;
}

interface SessionContextValue {
  user: SessionUser | null;
  mounted: boolean;
  /** 실 인증 경로 여부 — login/signup 페이지가 OTP UX 분기에 사용. */
  useApi: boolean;
  /** mock 즉시 로그인(USE_API=false — 테스트·오프라인 데모). */
  login: (user?: Partial<SessionUser>) => void;
  /** mock 즉시 가입. */
  signup: (user?: Partial<SessionUser>) => void;
  logout: () => void;
  /** OTP 발송(signup/otp) — 로그인·가입 공통 1단계. */
  requestOtp: (phone: string) => Promise<void>;
  /** OTP 로그인(기존 계정 재인증). 실패 시 ApiError — 422는 미가입·인증번호 오류가 섞여 오며 detail로 구분(login/page.tsx). */
  loginWithOtp: (phone: string, otp: string) => Promise<void>;
  /** OTP 가입(신규 계정). */
  signupWithOtp: (input: SignupInput) => Promise<void>;
}

const DEFAULT_USER: SessionUser = { id: "mock-me", name: "데모 유저", handle: "me", role: "fan" };

const SessionContext = React.createContext<SessionContextValue | null>(null);

// --- mock 경로(localStorage) -------------------------------------------------
const STORAGE_KEY = "assen.session";

function readStored(): SessionUser | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<SessionUser>;
    if (typeof parsed?.name === "string" && typeof parsed?.handle === "string") {
      return {
        id: typeof parsed.id === "string" ? parsed.id : DEFAULT_USER.id,
        name: parsed.name,
        handle: parsed.handle,
        role: parsed.role === "creator" ? "creator" : "fan",
        avatarUrl: typeof parsed.avatarUrl === "string" ? parsed.avatarUrl : undefined,
      };
    }
  } catch {
    /* 파싱 실패 무시 */
  }
  return null;
}

function MockSessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<SessionUser | null>(null);
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setUser(readStored());
    setMounted(true);
  }, []);

  const persist = React.useCallback((next: SessionUser | null) => {
    setUser(next);
    try {
      if (next) localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      else localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* 저장 실패 무시 */
    }
  }, []);

  const login = React.useCallback(
    (u?: Partial<SessionUser>) => persist({ ...DEFAULT_USER, ...u }),
    [persist],
  );
  const signup = React.useCallback(
    (u?: Partial<SessionUser>) => persist({ ...DEFAULT_USER, ...u }),
    [persist],
  );
  const logout = React.useCallback(() => persist(null), [persist]);

  // mock 모드에서도 OTP 계약 시그니처를 만족(즉시 로그인으로 합성 — 실 발송/검증 없음).
  const requestOtp = React.useCallback(async () => {}, []);
  const loginWithOtp = React.useCallback(async () => persist(DEFAULT_USER), [persist]);
  const signupWithOtp = React.useCallback(
    async (input: SignupInput) => persist({ ...DEFAULT_USER, name: input.nickname }),
    [persist],
  );

  const value = React.useMemo<SessionContextValue>(
    () => ({ user, mounted, useApi: false, login, signup, logout, requestOtp, loginWithOtp, signupWithOtp }),
    [user, mounted, login, signup, logout, requestOtp, loginWithOtp, signupWithOtp],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

// --- 실 인증 경로(React Query ['auth','me']) ---------------------------------
interface RawMe {
  id: string;
  nickname: string;
  role: string;
  handle?: string | null;
  avatar_url?: string | null;
}

async function fetchMe(): Promise<SessionUser | null> {
  try {
    const raw = await apiFetch<RawMe>("/fan/me");
    return {
      id: raw.id,
      name: raw.nickname,
      handle: raw.handle ?? raw.id,
      role: raw.role === "creator" ? "creator" : "fan",
      avatarUrl: raw.avatar_url ?? undefined,
    };
  } catch (e) {
    // 401 = 비로그인(정상 상태) → null. 그 외는 전파.
    if (e instanceof ApiError && e.status === 401) return null;
    throw e;
  }
}

function ApiSessionProvider({ children }: { children: React.ReactNode }) {
  const qc = useQueryClient();
  const meQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: fetchMe,
    staleTime: 60_000,
    retry: false,
  });

  const requestOtp = React.useCallback(async (phone: string) => {
    await apiFetch("/fan/signup/otp", { method: "POST", body: JSON.stringify({ phone }) });
  }, []);

  const loginWithOtp = React.useCallback(
    async (phone: string, otp: string) => {
      await apiFetch("/fan/login", {
        method: "POST",
        body: JSON.stringify({ phone, otp_code: otp, web: true }),
      });
      await qc.invalidateQueries({ queryKey: ["auth", "me"] });
    },
    [qc],
  );

  const signupWithOtp = React.useCallback(
    async (input: SignupInput) => {
      await apiFetch("/fan/signup", {
        method: "POST",
        body: JSON.stringify({
          phone: input.phone,
          otp_code: input.otp,
          nickname: input.nickname,
          consent_terms: input.consentTerms,
          consent_privacy: input.consentPrivacy,
          web: true,
        }),
      });
      await qc.invalidateQueries({ queryKey: ["auth", "me"] });
    },
    [qc],
  );

  const logout = React.useCallback(() => {
    void (async () => {
      try {
        await apiFetch("/fan/logout", { method: "POST" });
      } catch {
        /* 로그아웃 실패해도 로컬 세션은 비운다 */
      }
      qc.setQueryData(["auth", "me"], null);
      await qc.invalidateQueries({ queryKey: ["auth", "me"] });
    })();
  }, [qc]);

  const value = React.useMemo<SessionContextValue>(
    () => ({
      user: meQuery.data ?? null,
      mounted: !meQuery.isLoading,
      useApi: true,
      // 실 인증 모드에선 mock 즉시 로그인/가입은 사용하지 않음(페이지가 OTP 경로로 분기).
      login: () => {},
      signup: () => {},
      logout,
      requestOtp,
      loginWithOtp,
      signupWithOtp,
    }),
    [meQuery.data, meQuery.isLoading, logout, requestOtp, loginWithOtp, signupWithOtp],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  // USE_API는 모듈 상수 → 런타임 내내 동일 분기(훅 순서 안정).
  return USE_API ? (
    <ApiSessionProvider>{children}</ApiSessionProvider>
  ) : (
    <MockSessionProvider>{children}</MockSessionProvider>
  );
}

/** 세션 훅. `const { user, login, logout } = useSession()`. */
export function useSession(): SessionContextValue {
  const ctx = React.useContext(SessionContext);
  if (!ctx) {
    return {
      user: null,
      mounted: false,
      useApi: false,
      login: () => {},
      signup: () => {},
      logout: () => {},
      requestOtp: async () => {},
      loginWithOtp: async () => {},
      signupWithOtp: async () => {},
    };
  }
  return ctx;
}
