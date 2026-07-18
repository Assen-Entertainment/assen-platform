"use client";
import * as React from "react";

/**
 * ThemeProvider — 자체 구현(의존성 추가 금지). localStorage("theme")+prefers-color-scheme로
 * `<html class="dark">`를 토글한다. FOUC 방지 초기 적용은 layout `<head>`의 인라인 스크립트가
 * 담당(이 프로바이더는 하이드레이션 후 상태 동기화만 수행 → SSR 불일치 없음).
 */
export type Theme = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "theme";

interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (t: Theme) => void;
  /** 하이드레이션 완료 여부 — 토글 아이콘의 SSR 불일치 방지용. */
  mounted: boolean;
}

const ThemeContext = React.createContext<ThemeContextValue | null>(null);

function systemPrefersDark(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function resolve(theme: Theme): ResolvedTheme {
  if (theme === "system") return systemPrefersDark() ? "dark" : "light";
  return theme;
}

function applyClass(resolved: ResolvedTheme) {
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<Theme>("system");
  const [resolvedTheme, setResolvedTheme] = React.useState<ResolvedTheme>("light");
  const [mounted, setMounted] = React.useState(false);

  // 마운트 시 localStorage에서 복원(SSR에서는 실행 안 됨 → 불일치 방지).
  React.useEffect(() => {
    let stored: Theme = "system";
    try {
      const v = localStorage.getItem(STORAGE_KEY);
      if (v === "light" || v === "dark" || v === "system") stored = v;
    } catch {
      /* localStorage 접근 불가 환경(프라이빗 모드 등) — 기본값 유지 */
    }
    setThemeState(stored);
    const r = resolve(stored);
    setResolvedTheme(r);
    applyClass(r);
    setMounted(true);
  }, []);

  // system 모드일 때 OS 테마 변경 추종.
  React.useEffect(() => {
    if (theme !== "system") return;
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      const r: ResolvedTheme = mql.matches ? "dark" : "light";
      setResolvedTheme(r);
      applyClass(r);
    };
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [theme]);

  const setTheme = React.useCallback((next: Theme) => {
    setThemeState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* 저장 실패 무시 */
    }
    const r = resolve(next);
    setResolvedTheme(r);
    applyClass(r);
  }, []);

  const value = React.useMemo<ThemeContextValue>(
    () => ({ theme, resolvedTheme, setTheme, mounted }),
    [theme, resolvedTheme, setTheme, mounted],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

/** 테마 훅. `const { resolvedTheme, setTheme } = useTheme()`. */
export function useTheme(): ThemeContextValue {
  const ctx = React.useContext(ThemeContext);
  if (!ctx) {
    // Provider 밖 사용 시 안전 폴백(테스트/독립 렌더).
    return { theme: "system", resolvedTheme: "light", setTheme: () => {}, mounted: false };
  }
  return ctx;
}

/**
 * FOUC 방지 인라인 스크립트 — layout `<head>`에서 실행. React 하이드레이션 전에
 * localStorage/OS 설정을 읽어 즉시 `.dark`를 적용한다(테마 깜빡임 제거).
 */
export const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem("theme");var d=window.matchMedia("(prefers-color-scheme: dark)").matches;if(t==="dark"||((t===null||t==="system")&&d)){document.documentElement.classList.add("dark");}}catch(e){}})();`;
