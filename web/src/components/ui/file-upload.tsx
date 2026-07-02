"use client";
import * as React from "react";
import { cn } from "@/lib/utils";
import { UploadIcon } from "@/lib/icons";

/** FileUpload — 드래그앤드롭 + 클릭 업로드. 작성/프로필 이미지용. 커스텀(무의존). */
export interface FileUploadProps {
  onFiles: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  label?: string;
  className?: string;
}

export function FileUpload({ onFiles, accept, multiple, label = "파일을 끌어다 놓거나 클릭해 업로드", className }: FileUploadProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [over, setOver] = React.useState(false);
  const pick = (fl: FileList | null) => {
    if (fl && fl.length) onFiles(Array.from(fl));
  };
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        pick(e.dataTransfer.files);
      }}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center text-body-s transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
        over ? "border-primary bg-primary-container text-on-primary-container" : "border-outline text-on-surface-variant hover:bg-surface-container-high",
        className,
      )}
    >
      <UploadIcon className="size-6" />
      {label}
      <input ref={inputRef} type="file" accept={accept} multiple={multiple} className="hidden" onChange={(e) => pick(e.target.files)} />
    </div>
  );
}
