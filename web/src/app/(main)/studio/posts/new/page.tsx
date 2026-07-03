"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import {
  TextField,
  TextArea,
  FileUpload,
  Switch,
  Button,
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
  SafetyGuideNotice,
} from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { validateComposerDraft, VISIBILITY_OPTIONS, type PostVisibility } from "@/lib/studio-mock";

/**
 * Post Composer — Figma Web-Composer(154:90) / W3.
 * 제목·본문·이미지 슬롯·공개범위·19+ 토글 → 임시저장/발행(mock → 토스트 → /studio).
 * ※실 업로드/발행 백엔드 미연동(B2 게이트). 파일은 로컬 미리보기만.
 */
export default function PostComposerPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [title, setTitle] = React.useState("");
  const [body, setBody] = React.useState("");
  const [visibility, setVisibility] = React.useState<PostVisibility>("public");
  const [adult, setAdult] = React.useState(false);
  const [files, setFiles] = React.useState<File[]>([]);
  const [submitted, setSubmitted] = React.useState(false);

  const validation = validateComposerDraft({ title, body, visibility, adult });
  const visHint = VISIBILITY_OPTIONS.find((o) => o.value === visibility)?.hint;

  const publish = () => {
    setSubmitted(true);
    if (!validation.valid) return;
    // mock 발행 — 실제 저장 없음(게이트).
    toast({ title: "발행되었어요", description: "포스트가 게시되었습니다. (데모 — 실제 저장 안 됨)" });
    router.push("/studio");
  };

  const saveDraft = () => {
    // mock 임시저장 — 제목/본문 없이도 허용.
    toast({ title: "임시저장됨", description: "작성 중인 내용을 임시저장했어요. (데모)" });
    router.push("/studio");
  };

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5">
      <h1 className="text-headline text-on-surface">새 포스트</h1>

      <TextField
        label="제목"
        placeholder="포스트 제목"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        maxLength={60}
        error={submitted && !!validation.errors.title}
        errorText={validation.errors.title}
      />

      <TextArea
        label="본문"
        placeholder="팬들에게 전하고 싶은 이야기를 적어보세요."
        value={body}
        onChange={(e) => setBody(e.target.value)}
        maxLength={2000}
        showCount
        className="min-h-40"
        error={submitted && !!validation.errors.body}
        errorText={validation.errors.body}
      />

      <div className="flex flex-col gap-2">
        <span className="text-label text-on-surface">이미지</span>
        <FileUpload accept="image/*" multiple onFiles={(f) => setFiles((prev) => [...prev, ...f])} />
        {files.length > 0 ? (
          <ul className="flex flex-wrap gap-2" aria-label="선택한 이미지">
            {files.map((f, i) => (
              <li
                key={`${f.name}-${i}`}
                className="flex items-center gap-2 rounded-md border border-outline bg-surface-container px-2.5 py-1.5 text-caption text-on-surface-variant"
              >
                <span className="max-w-40 truncate">{f.name}</span>
                <button
                  type="button"
                  aria-label={`${f.name} 제거`}
                  onClick={() => setFiles((prev) => prev.filter((_, j) => j !== i))}
                  className="text-on-surface-variant hover:text-error"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="composer-visibility" className="text-label text-on-surface">
          공개 범위
        </label>
        <Select value={visibility} onValueChange={(v) => setVisibility(v as PostVisibility)}>
          <SelectTrigger id="composer-visibility" aria-label="공개 범위">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {VISIBILITY_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {visHint ? <p className="text-caption text-on-surface-variant">{visHint}</p> : null}
      </div>

      <div className="flex items-start justify-between gap-3 rounded-md border border-outline bg-surface p-4">
        <div className="flex min-w-0 flex-col gap-0.5">
          <span className="text-label text-on-surface">19+ 성인 콘텐츠</span>
          <span className="text-caption text-on-surface-variant">
            켜면 만 19세 이상 인증 이용자에게만 노출되고, 목록에서 블러 처리됩니다.
          </span>
        </div>
        <Switch aria-label="19세 이상 성인 콘텐츠" checked={adult} onCheckedChange={setAdult} />
      </div>

      {adult ? (
        <SafetyGuideNotice title="성인 콘텐츠 안내">
          업로드 콘텐츠는 청소년 보호 및 관련 법령을 준수해야 하며, 위반 시 게시가 제한될 수 있어요. (문구는 법무 검토 전 초안)
        </SafetyGuideNotice>
      ) : null}

      <div className="sticky bottom-0 -mx-1 flex gap-2 border-t border-outline bg-surface/95 py-3 backdrop-blur">
        <Button variant="outline" className="flex-1" onClick={saveDraft}>
          임시저장
        </Button>
        <Button className="flex-1" onClick={publish}>
          발행하기
        </Button>
      </div>
      <p className="text-center text-caption text-on-surface-variant">※ 데모 — 실제 업로드·발행 미연동(게이트)</p>
    </div>
  );
}
