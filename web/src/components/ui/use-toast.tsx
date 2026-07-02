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
    setItems((prev) => [...prev, { id, ...t }]);
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
