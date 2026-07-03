"use client";
// ※ mock 세션 — 실 인증(B3)은 #26 인간 리뷰 게이트. 실 크리덴셜/토큰 저장 금지.
//   여기서는 UI 종단(로그인/가입/로그아웃 흐름·유저명 표시)만 위해 로컬 mock 유저를
//   localStorage에 보관한다. 비밀번호·토큰·개인정보는 절대 저장하지 않는다.
import * as React from "react";

export interface SessionUser {
  name: string;
  handle: string;
  role: "fan" | "creator";
}

const STORAGE_KEY = "assen.session";

interface SessionContextValue {
  user: SessionUser | null;
  /** mock 로그인 — 데모 유저를 세션에 기록(실 인증 아님). */
  login: (user?: Partial<SessionUser>) => void;
  /** mock 가입 — 로그인과 동일하게 데모 유저를 기록. */
  signup: (user?: Partial<SessionUser>) => void;
  logout: () => void;
  mounted: boolean;
}

const DEFAULT_USER: SessionUser = { name: "데모 유저", handle: "me", role: "fan" };

const SessionContext = React.createContext<SessionContextValue | null>(null);

function readStored(): SessionUser | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<SessionUser>;
    if (typeof parsed?.name === "string" && typeof parsed?.handle === "string") {
      return { name: parsed.name, handle: parsed.handle, role: parsed.role === "creator" ? "creator" : "fan" };
    }
  } catch {
    /* 파싱 실패 무시 */
  }
  return null;
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
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

  const value = React.useMemo<SessionContextValue>(
    () => ({ user, login, signup, logout, mounted }),
    [user, login, signup, logout, mounted],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

/** 세션 훅. `const { user, login, logout } = useSession()`. */
export function useSession(): SessionContextValue {
  const ctx = React.useContext(SessionContext);
  if (!ctx) {
    return { user: null, login: () => {}, signup: () => {}, logout: () => {}, mounted: false };
  }
  return ctx;
}
