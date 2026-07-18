"use client";
import * as React from "react";

/**
 * useDebouncedValue — value가 delay(ms) 동안 변하지 않으면 그 값을 반환(디바운스).
 * 검색 서제스트처럼 타이핑 중간 요청을 억제할 때 사용. 언마운트/재입력 시 타이머 정리.
 */
export function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}
