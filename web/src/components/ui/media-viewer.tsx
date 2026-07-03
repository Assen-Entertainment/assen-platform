"use client";
import * as React from "react";
import { cn } from "@/lib/utils";
import { CloseIcon } from "@/lib/icons";
import { gradientStyle } from "@/lib/placeholder";

/**
 * MediaViewer — Figma Web-MediaViewer(178:263). 포스트 미디어 풀스크린 라이트박스.
 * 키 핸들링(ESC 닫기) + 배경 클릭 닫기 + 포커스 트랩/복귀 + aria-modal(루브릭 #53).
 * 실 이미지 자산 게이트 → seed 파생 그라디언트로 대체 렌더.
 */
export interface MediaViewerProps {
  open: boolean;
  onClose: () => void;
  /** 그라디언트 대체 아트 seed(포스트 id·제목 등). */
  seed: string;
  caption?: string;
  /** 대체 텍스트(스크린리더). */
  alt?: string;
}

export function MediaViewer({ open, onClose, seed, caption, alt = "포스트 미디어" }: MediaViewerProps) {
  const closeRef = React.useRef<HTMLButtonElement>(null);
  const prevFocus = React.useRef<HTMLElement | null>(null);

  React.useEffect(() => {
    if (!open) return;
    // 열릴 때 이전 포커스 저장 → 닫기 버튼으로 이동, 닫힐 때 복귀.
    prevFocus.current = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    // 배경 스크롤 잠금 — 라이트박스가 열린 동안 body 스크롤 방지, 닫힐 때 원복.
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prevOverflow;
      prevFocus.current?.focus?.();
    };
  }, [open]);

  if (!open) return null;

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    } else if (e.key === "Tab") {
      // 단일 인터랙티브(닫기)만 존재 → 포커스를 내부에 가둔다.
      e.preventDefault();
      closeRef.current?.focus();
    }
  };

  // 배경(root 자신) 클릭만 닫는다 — 콘텐츠(자식) 클릭은 target≠currentTarget 이라 무시.
  const onBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={alt}
      tabIndex={-1}
      onKeyDown={onKeyDown}
      onClick={onBackdropClick}
      className="fixed inset-0 z-[60] flex flex-col items-center justify-center gap-4 bg-black/85 p-4 [animation:success-pop_180ms_ease-out]"
    >
      <button
        ref={closeRef}
        type="button"
        aria-label="닫기"
        onClick={onClose}
        className="absolute right-4 top-4 flex size-10 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-white/20 [&>svg]:size-6"
      >
        <CloseIcon />
      </button>

      <div className={cn("flex max-h-[80vh] w-full max-w-3xl flex-col gap-3")}>
        <div className="aspect-video w-full overflow-hidden rounded-lg" style={gradientStyle(seed)} role="img" aria-label={alt} />
        {caption ? <p className="text-center text-body-m text-white/90">{caption}</p> : null}
      </div>
    </div>
  );
}
