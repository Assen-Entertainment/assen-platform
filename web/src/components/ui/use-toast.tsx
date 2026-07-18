"use client";
import * as React from "react";
import { ToastProvider, ToastViewport, Toast, ToastTitle, ToastDescription, ToastClose } from "./toast";
import { CloseIcon } from "@/lib/icons";

/** Toast 입력. */
export interface ToastInput {
  title?: string;
  description?: string;
}
interface ToastItem extends ToastInput {
  id: number;
}

/** 동시 표시 상한(R5-W3 #2) — 초과 시 가장 오래된 것부터 제거. */
export const MAX_TOASTS = 3;

/**
 * 토스트 큐 정책(R5-W3 #2) — 순수 함수(테스트 대상).
 * - 최신 토스트와 title+description이 모두 같으면 새로 쌓지 않고 마지막 항목을 새 id로 교체
 *   (연속 중복 병합·타이머 리셋). title만 같고 내용(description)이 다르면 병합하지 않는다(내용 유실 방지).
 * - 그 외엔 append 하되 동시 개수를 MAX_TOASTS로 제한(초과분은 오래된 것부터 제거).
 */
export function reduceToastQueue(prev: ToastItem[], input: ToastInput, nextId: number): ToastItem[] {
  const last = prev[prev.length - 1];
  if (last && last.title === input.title && last.description === input.description) {
    return [...prev.slice(0, -1), { id: nextId, ...input }];
  }
  const next = [...prev, { id: nextId, ...input }];
  return next.length > MAX_TOASTS ? next.slice(next.length - MAX_TOASTS) : next;
}

const ToastContext = React.createContext<(t: ToastInput) => void>(() => {
  if (process.env.NODE_ENV !== "production") {
    // Toaster 밖에서 useToast 호출 시 조용히 무시(개발 경고).
    console.warn("useToast() 는 <Toaster> 하위에서만 동작합니다.");
  }
});

/** 토스트 발행 훅. `const { toast } = useToast(); toast({ title, description })`. */
export function useToast() {
  const toast = React.useContext(ToastContext);
  return { toast };
}

/** 루트에 1회 배치. children 을 감싸 Toast viewport 를 제공. */
export function Toaster({ children }: { children: React.ReactNode }) {
  const [items, setItems] = React.useState<ToastItem[]>([]);
  const idRef = React.useRef(0);

  const toast = React.useCallback((t: ToastInput) => {
    idRef.current += 1;
    const id = idRef.current;
    // 상한·중복 병합은 reduceToastQueue(순수)로 위임 — updater는 멱등(같은 prev/id에서 동일 결과).
    setItems((prev) => reduceToastQueue(prev, t, id));
  }, []);

  const remove = React.useCallback((id: number) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={toast}>
      <ToastProvider swipeDirection="right" duration={3000}>
        {children}
        {items.map((i) => (
          <Toast
            key={i.id}
            onOpenChange={(open) => {
              if (!open) remove(i.id);
            }}
          >
            <div className="flex min-w-0 flex-col gap-0.5">
              {i.title ? <ToastTitle>{i.title}</ToastTitle> : null}
              {i.description ? <ToastDescription>{i.description}</ToastDescription> : null}
            </div>
            <ToastClose aria-label="닫기" className="shrink-0 text-on-surface-variant hover:text-on-surface [&>svg]:size-5">
              <CloseIcon />
            </ToastClose>
          </Toast>
        ))}
        <ToastViewport />
      </ToastProvider>
    </ToastContext.Provider>
  );
}
