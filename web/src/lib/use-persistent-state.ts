"use client";
import * as React from "react";

/**
 * usePersistentToggle — boolean 상태를 localStorage 에 영속.
 * 마운트 후 복원(SSR 불일치 방지). 설정 화면 스위치 등에 사용.
 * 저장 실패(프라이빗 모드 등)는 조용히 무시하고 in-memory 로 동작.
 */
export function usePersistentToggle(key: string, defaultValue: boolean): [boolean, (v: boolean) => void] {
  const [value, setValue] = React.useState(defaultValue);
  React.useEffect(() => {
    try {
      const v = localStorage.getItem(key);
      if (v !== null) setValue(v === "1");
    } catch {
      /* 접근 불가 무시 */
    }
  }, [key]);
  const update = React.useCallback(
    (next: boolean) => {
      setValue(next);
      try {
        localStorage.setItem(key, next ? "1" : "0");
      } catch {
        /* 저장 실패 무시 */
      }
    },
    [key],
  );
  return [value, update];
}
