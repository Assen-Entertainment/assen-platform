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
import { apiSignupEmail, apiLoginEmail, apiVerifyEmail } from "@/lib/api";
import { track } from "@/lib/analytics";

const USE_API = Boolean(config.apiUrl);

/** KYC(본인인증) 상태 — 서버 kyc_status enum 미러. 미확정 값은 fail-closed로 "unverified". */
export type KycStatus = "unverified" | "pending" | "verified" | "failed";

const KYC_STATUSES: readonly KycStatus[] = ["unverified", "pending", "verified", "failed"];

/** 서버 kyc_status 문자열을 안전한 enum으로 강제(미지의 값 → unverified, fail-closed). */
export function coerceKycStatus(raw: unknown): KycStatus {
  return typeof raw === "string" && (KYC_STATUSES as readonly string[]).includes(raw)
    ? (raw as KycStatus)
    : "unverified";
}

export interface SessionUser {
  id: string;
  name: string;
  handle: string;
  role: "fan" | "creator";
  avatarUrl?: string;
  /** 크리에이터 페이지 운영 여부 — /fan/me의 handle 존재로 파생(Role enum엔 creator 값이 없음). */
  isCreator: boolean;
  /** 성인(19+) 인증 여부 — 파생 플래그(원본 PII 아님). 기본 fail-closed=false. */
  adultVerified: boolean;
  /** 본인인증 상태 — KYC 배너·게이팅 분기. 기본 fail-closed="unverified". */
  kycStatus: KycStatus;
}

/** OTP 가입 입력. */
export interface SignupInput {
  phone: string;
  otp: string;
  nickname: string;
  consentTerms: boolean;
  consentPrivacy: boolean;
  /** 만 14세 이상 확인(D5). 서버는 미전송을 fail-closed로 거부(SignupIn 기본 false). */
  ageOver14: boolean;
  /** 마케팅 수신(선택). true면 서버가 SMS 옵트인만 기록(가입 시 도달 채널=전화). */
  marketingConsent?: boolean;
}

/** 이메일 가입 입력(B1: 폰 OTP 대체). 서버 EmailSignupIn 미러(모든 동의 bool 명시). */
export interface EmailSignupInput {
  email: string;
  password: string;
  nickname: string;
  consentTerms: boolean;
  consentPrivacy: boolean;
  /** 만 14세 이상 확인(D5). 서버는 미전송을 fail-closed로 거부(EmailSignupIn 기본 false). */
  ageOver14: boolean;
  /** 마케팅 수신(선택). */
  marketingConsent: boolean;
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
  /**
   * 이메일 가입(B1) — 토큰/세션 미발급. 인증 메일 발송 후 verificationToken을 반환한다
   * (dev/test에서만 비어있지 않음 — verify-email 개발용 링크에 사용). 실 로그인은 verifyEmail에서.
   */
  signupWithEmail: (input: EmailSignupInput) => Promise<{ verificationToken: string }>;
  /** 이메일 로그인(기존 계정). 실패 시 ApiError — 422 InvalidCredentials·403 EmailNotVerified(login/page.tsx). */
  loginWithEmail: (email: string, password: string) => Promise<void>;
  /** 이메일 인증 확인(verify-email 링크) — 성공 시 세션 발급(로그인 상태). 400 EmailVerificationInvalid. */
  verifyEmail: (token: string) => Promise<void>;
  /** 셀프 "크리에이터 되기" — POST /studio/profile 후 세션 갱신. 실패 시 ApiError 전파. */
  becomeCreator: (input: { handle: string; name: string }) => Promise<void>;
  /**
   * 본인인증 완료 결과를 세션에 반영 — mock은 로컬 persist, 실 경로는 ['auth','me'] 갱신.
   * age-gate/KYC 확인 성공 후 호출(파생 플래그만 — 원본 PII 미보관).
   */
  markAdultVerified: (result: { adultVerified: boolean; kycStatus: string }) => void;
  /** 소셜 로그인 시작 — provider start 조회 후 브라우저를 authorize_url로 리다이렉트(현 페이지 이탈). */
  startSocial: (provider: string, next?: string) => Promise<void>;
  /** 소셜 콜백 완료 — provider callback POST(implied consent) 후 세션 갱신. 실패 시 ApiError 전파. */
  completeSocial: (input: { provider: string; code: string; state: string }) => Promise<void>;
}

// mock 기본값은 fail-closed — 성인 인증 미완료(adultVerified:false·kycStatus:"unverified").
const DEFAULT_USER: SessionUser = {
  id: "mock-me",
  name: "데모 유저",
  handle: "me",
  role: "fan",
  isCreator: false,
  adultVerified: false,
  kycStatus: "unverified",
};

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
        // 크리에이터 여부는 mock에선 명시 저장값으로 복원(fail-closed).
        isCreator: parsed.isCreator === true,
        // 인증 플래그는 fail-closed 복원 — 저장값이 참일 때만 유지.
        adultVerified: parsed.adultVerified === true,
        kycStatus: coerceKycStatus(parsed.kycStatus),
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
    (u?: Partial<SessionUser>) => {
      persist({ ...DEFAULT_USER, ...u });
      track("login_completed", { method: "mock" });
    },
    [persist],
  );
  const signup = React.useCallback(
    (u?: Partial<SessionUser>) => {
      persist({ ...DEFAULT_USER, ...u });
      track("signup_completed", { method: "mock" });
    },
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

  // mock: 이메일 계약도 합성. 가입은 세션을 세우지 않고(실 경로처럼 인증 메일 단계 모사) 빈
  // 토큰을 반환하며, 로그인·인증 확인은 즉시 DEFAULT_USER를 persist(오프라인·CI).
  const signupWithEmail = React.useCallback(async () => {
    track("signup_completed", { method: "email" });
    return { verificationToken: "" };
  }, []);
  const loginWithEmail = React.useCallback(
    async () => {
      persist(DEFAULT_USER);
      track("login_completed", { method: "email" });
    },
    [persist],
  );
  const verifyEmail = React.useCallback(
    async () => {
      persist(DEFAULT_USER);
      track("signup_completed", { method: "email" });
    },
    [persist],
  );
  // mock: 크리에이터 전환을 로컬 세션에 반영(handle + isCreator).
  const becomeCreator = React.useCallback(
    async ({ handle, name }: { handle: string; name: string }) =>
      persist({ ...(user ?? DEFAULT_USER), handle, name, isCreator: true }),
    [persist, user],
  );
  // mock: 인증 완료 플래그를 로컬 세션에 반영(로그인 상태가 없으면 DEFAULT_USER를 기준으로 합성).
  const markAdultVerified = React.useCallback(
    (result: { adultVerified: boolean; kycStatus: string }) =>
      persist({
        ...(user ?? DEFAULT_USER),
        adultVerified: result.adultVerified,
        kycStatus: coerceKycStatus(result.kycStatus),
      }),
    [persist, user],
  );

  // mock: 소셜 로그인도 즉시 로그인으로 합성(실 리다이렉트/콜백 없음 — 오프라인·CI).
  const startSocial = React.useCallback(async () => persist(DEFAULT_USER), [persist]);
  const completeSocial = React.useCallback(async () => persist(DEFAULT_USER), [persist]);

  const value = React.useMemo<SessionContextValue>(
    () => ({ user, mounted, useApi: false, login, signup, logout, requestOtp, loginWithOtp, signupWithOtp, signupWithEmail, loginWithEmail, verifyEmail, becomeCreator, markAdultVerified, startSocial, completeSocial }),
    [user, mounted, login, signup, logout, requestOtp, loginWithOtp, signupWithOtp, signupWithEmail, loginWithEmail, verifyEmail, becomeCreator, markAdultVerified, startSocial, completeSocial],
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
  adult_verified?: boolean;
  kyc_status?: string;
}

/** /fan/me(FanMeOut) → SessionUser 매핑. 인증 플래그는 fail-closed(누락/미지값→false·unverified). */
export function mapMe(raw: RawMe): SessionUser {
  return {
    id: raw.id,
    name: raw.nickname,
    handle: raw.handle ?? raw.id,
    role: raw.role === "creator" ? "creator" : "fan",
    avatarUrl: raw.avatar_url ?? undefined,
    // 크리에이터 = 크리에이터 프로필 운영 여부. 서버 role엔 creator 값이 없어(fan/staff만)
    // raw.handle 존재(널 아님)로 파생한다 — role 기반 분기가 매칭 안 되던 버그의 정본 신호.
    isCreator: raw.handle != null,
    adultVerified: raw.adult_verified === true,
    kycStatus: coerceKycStatus(raw.kyc_status),
  };
}

async function fetchMe(): Promise<SessionUser | null> {
  try {
    return mapMe(await apiFetch<RawMe>("/fan/me"));
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
      track("login_completed", { method: "otp" });
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
          age_over_14: input.ageOver14,
          marketing_consent: input.marketingConsent ?? false,
          web: true,
        }),
      });
      await qc.invalidateQueries({ queryKey: ["auth", "me"] });
      track("signup_completed", { method: "otp" });
    },
    [qc],
  );

  // 이메일 가입(B1) — 토큰/세션 미발급(인증 메일 발송까지). verificationToken은 dev/test에서만
  // 비어있지 않다(verify-email 개발용 링크). ['auth','me'] 무효화 없음(아직 로그인 아님).
  const signupWithEmail = React.useCallback(async (input: EmailSignupInput) => {
    return apiSignupEmail(input);
  }, []);

  const loginWithEmail = React.useCallback(
    async (email: string, password: string) => {
      await apiLoginEmail({ email, password });
      await qc.invalidateQueries({ queryKey: ["auth", "me"] });
      track("login_completed", { method: "email" });
    },
    [qc],
  );

  const verifyEmail = React.useCallback(
    async (token: string) => {
      await apiVerifyEmail(token);
      await qc.invalidateQueries({ queryKey: ["auth", "me"] });
      // verify-email은 가입의 종단(첫 인증)이자 로그인 — 가입 완료로 계측한다.
      track("signup_completed", { method: "email" });
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

  // 실 경로: 인증 결과를 ['auth','me'] 캐시에 즉시 반영 후 재조회로 정정.
  const markAdultVerified = React.useCallback(
    (result: { adultVerified: boolean; kycStatus: string }) => {
      qc.setQueryData<SessionUser | null>(["auth", "me"], (u) =>
        u ? { ...u, adultVerified: result.adultVerified, kycStatus: coerceKycStatus(result.kycStatus) } : u,
      );
      void qc.invalidateQueries({ queryKey: ["auth", "me"] });
    },
    [qc],
  );

  // 실 경로: 셀프 크리에이터 등록 후 ['auth','me'] 재조회로 handle(=isCreator 신호)을 반영.
  const becomeCreator = React.useCallback(
    async ({ handle, name }: { handle: string; name: string }) => {
      await apiFetch("/studio/profile", {
        method: "POST",
        body: JSON.stringify({ handle, name }),
      });
      await qc.invalidateQueries({ queryKey: ["auth", "me"] });
    },
    [qc],
  );

  const startSocial = React.useCallback(async (provider: string, next = "/discovery") => {
    // next는 콜백 후 복귀 경로 — provider 리다이렉트가 쿼리를 덮어쓰므로 sessionStorage로 전달.
    try {
      sessionStorage.setItem("assen.social.next", next);
    } catch {
      /* storage 불가 무시 — 콜백은 기본 /discovery로 복귀 */
    }
    const redirectUri = `${window.location.origin}/auth/callback/${provider}`;
    const { authorize_url } = await apiFetch<{ authorize_url: string; state: string }>(
      `/fan/social/${provider}/start?redirect_uri=${encodeURIComponent(redirectUri)}`,
    );
    window.location.href = authorize_url;
  }, []);

  const completeSocial = React.useCallback(
    async ({ provider, code, state }: { provider: string; code: string; state: string }) => {
      const redirectUri = `${window.location.origin}/auth/callback/${provider}`;
      // Implied consent: 사용자가 소셜 버튼 옆 고지(이용약관·개인정보·만 14세)를 지나 진행함.
      await apiFetch(`/fan/social/${provider}/callback`, {
        method: "POST",
        body: JSON.stringify({
          code,
          state,
          redirect_uri: redirectUri,
          consent_terms: true,
          consent_privacy: true,
          age_over_14: true,
          web: true,
        }),
      });
      await qc.invalidateQueries({ queryKey: ["auth", "me"] });
      track("login_completed", { method: "social" });
    },
    [qc],
  );

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
      signupWithEmail,
      loginWithEmail,
      verifyEmail,
      becomeCreator,
      markAdultVerified,
      startSocial,
      completeSocial,
    }),
    [meQuery.data, meQuery.isLoading, logout, requestOtp, loginWithOtp, signupWithOtp, signupWithEmail, loginWithEmail, verifyEmail, becomeCreator, markAdultVerified, startSocial, completeSocial],
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
      signupWithEmail: async () => ({ verificationToken: "" }),
      loginWithEmail: async () => {},
      verifyEmail: async () => {},
      becomeCreator: async () => {},
      markAdultVerified: () => {},
      startSocial: async () => {},
      completeSocial: async () => {},
    };
  }
  return ctx;
}
