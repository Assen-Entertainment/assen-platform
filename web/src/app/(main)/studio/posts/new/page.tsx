"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import {
  TextField,
  TextArea,
  FileUpload,
  Switch,
  Button,
  Spinner,
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
  SafetyGuideNotice,
} from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { config } from "@/lib/config";
import { ApiError, apiErrorMessage } from "@/lib/api";
import { usePublishPost, useUploadImage, useStudioTiers } from "@/lib/api/queries";
import { validateComposerDraft, VISIBILITY_OPTIONS, type PostVisibility } from "@/lib/studio-mock";

/**
 * Post Composer — Figma Web-Composer(154:90) / W3.
 * 제목·본문·이미지 슬롯·공개범위·19+ 토글 → 임시저장/발행(mock → 토스트 → /studio).
 * ※이미지는 선택 즉시 POST /api/uploads로 업로드해 media_url을 확보하고(라이브), mock 모드는
 *   로컬 미리보기 URL만 쓴다. 발행 시 확보한 media_url을 PostIn에 실어 보낸다.
 */
export default function PostComposerPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [title, setTitle] = React.useState("");
  const [body, setBody] = React.useState("");
  const [visibility, setVisibility] = React.useState<PostVisibility>("public");
  // "특정 티어 이상"(tier) 선택 시 게이트할 티어 id. useStudioTiers에서 채운다(오너 자기 티어).
  const [tierId, setTierId] = React.useState("");
  const [adult, setAdult] = React.useState(false);
  // 업로드 완료된 이미지 media_url(서버가 준 /media/uploads/… 또는 mock objectURL). 발행 시 PostIn에 실린다.
  const [mediaUrl, setMediaUrl] = React.useState<string | undefined>(undefined);
  const [submitted, setSubmitted] = React.useState(false);
  const publishPost = usePublishPost();
  const uploadImage = useUploadImage();
  const tiersQuery = useStudioTiers();
  const tiers = tiersQuery.data ?? [];
  const live = Boolean(config.apiUrl);
  // "특정 티어 이상"인데 티어 미선택이면 발행 불가(서버 required_tier 검증 전 클라 가드).
  const tierMissing = visibility === "tier" && !tierId;

  // mock 폴백(USE_API=false)의 미리보기 URL은 URL.createObjectURL(blob:) — 교체/제거·언마운트 시
  // 해제하지 않으면 브라우저에 objectURL이 누적된다. 이 cleanup은 mediaUrl이 blob:일 때만 revoke하며
  // (라이브 서버 URL `/media/uploads/…`은 무영향), mediaUrl 변경(교체·undefined)·언마운트에서 이전 값을 해제한다.
  React.useEffect(() => {
    if (!mediaUrl || !mediaUrl.startsWith("blob:")) return;
    return () => URL.revokeObjectURL(mediaUrl);
  }, [mediaUrl]);

  const validation = validateComposerDraft({ title, body, visibility, adult });
  const visHint = VISIBILITY_OPTIONS.find((o) => o.value === visibility)?.hint;

  // 이미지 선택 즉시 업로드 → 반환 URL을 media_url로 확정(프리뷰). 실패는 코드 매핑 토스트로 안내.
  const onPickImage = (picked: File[]) => {
    const file = picked[0];
    if (!file) return;
    uploadImage.mutate(file, {
      onSuccess: ({ url }) => setMediaUrl(url),
      onError: (e) => {
        // 401은 전역 세션 가드가 처리 → 그 외만 업로드 실패로 안내(서버 code→apiErrorMessage).
        if (e instanceof ApiError && e.status === 401) return;
        toast({ title: "이미지를 올리지 못했어요", description: apiErrorMessage(e) });
      },
    });
  };

  const publish = () => {
    setSubmitted(true);
    if (!validation.valid || tierMissing || publishPost.isPending || uploadImage.isPending) return;
    // 제목은 본문 상단에 합성(서버 계약 PostIn={body, media_url?, is_adult, visibility, required_tier} — 제목 필드 없음).
    const composed = title.trim() ? `${title.trim()}\n\n${body}` : body;
    // UI 공개범위 → 서버 계약 매핑: public=전체 공개, members=구독자 전체, tier=특정 티어(required_tier).
    const serverVisibility: "public" | "members" = visibility === "public" ? "public" : "members";
    const requiredTier = visibility === "tier" ? tierId : undefined;
    // 19+ 등급은 실 전송하되, 실제 노출은 서버 ENABLE_ADULT_CONTENT=False가 통제(등급만 기록).
    publishPost.mutate(
      { body: composed, mediaUrl, isAdult: adult, visibility: serverVisibility, requiredTier },
      {
        onSuccess: () => {
          toast({
            title: "발행되었어요",
            description: live ? "포스트가 게시되었습니다." : "포스트가 게시되었습니다. (데모 — 실제 저장 안 됨)",
          });
          router.push("/studio");
        },
        onError: (e) => {
          // 크리에이터 오너만 발행 가능(서버 403). 그 외는 일반 실패 안내.
          if (e instanceof ApiError && e.status === 403) {
            toast({ title: "크리에이터 계정이 필요해요", description: "포스트 발행은 크리에이터 계정에서만 가능해요." });
          } else if (!(e instanceof ApiError && e.status === 401)) {
            // 401은 전역 세션 가드가 처리 → 여기선 그 외 오류만 안내.
            toast({ title: "발행하지 못했어요", description: "잠시 후 다시 시도해 주세요." });
          }
        },
      },
    );
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
        {uploadImage.isPending ? (
          <div
            className="flex items-center justify-center gap-2 rounded-lg border-2 border-dashed border-outline p-8 text-body-s text-on-surface-variant"
            aria-live="polite"
          >
            <Spinner className="size-5" /> 업로드 중…
          </div>
        ) : mediaUrl ? (
          <div className="relative w-fit">
            {/* 업로드된 이미지 프리뷰 — next/image 대신 <img>(objectURL/외부 media 오리진 모두 수용). */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={mediaUrl}
              alt="업로드한 이미지 미리보기"
              className="max-h-64 rounded-lg border border-outline object-contain"
            />
            <button
              type="button"
              aria-label="이미지 제거"
              onClick={() => setMediaUrl(undefined)}
              className="absolute right-2 top-2 rounded-full bg-surface/90 px-2 py-0.5 text-caption text-on-surface-variant shadow hover:text-error"
            >
              ✕
            </button>
          </div>
        ) : (
          <FileUpload accept="image/png,image/jpeg,image/webp,image/gif" onFiles={onPickImage} />
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="composer-visibility" className="text-label text-on-surface">
          공개 범위
        </label>
        {/* 서버 PostIn.visibility(public|members)+required_tier로 실 전송. "특정 티어 이상"은
            visibility=members + 선택 티어를 required_tier로 매핑(발행 시 publish()에서 변환). */}
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

        {/* "특정 티어 이상" 선택 시 오너 자기 티어에서 공개할 티어를 고른다(useStudioTiers). */}
        {visibility === "tier" ? (
          <div className="mt-1 flex flex-col gap-1.5">
            <label htmlFor="composer-tier" className="text-label text-on-surface">
              공개할 티어
            </label>
            {tiers.length > 0 ? (
              <Select value={tierId} onValueChange={setTierId}>
                <SelectTrigger id="composer-tier" aria-label="공개할 티어">
                  <SelectValue placeholder="티어를 선택하세요" />
                </SelectTrigger>
                <SelectContent>
                  {tiers.map((t) => (
                    <SelectItem key={t.id} value={t.id}>
                      {t.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <p className="text-caption text-on-surface-variant">
                {tiersQuery.isLoading
                  ? "티어를 불러오는 중이에요…"
                  : "먼저 멤버십 티어를 만들면 특정 티어로 공개할 수 있어요."}
              </p>
            )}
            {submitted && tierMissing ? (
              <p className="text-caption text-error">공개할 티어를 선택해 주세요.</p>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="flex items-start justify-between gap-3 rounded-md border border-outline bg-surface p-4">
        <div className="flex min-w-0 flex-col gap-0.5">
          <span className="text-label text-on-surface">19+ 성인 콘텐츠</span>
          <span className="text-caption text-on-surface-variant">
            켜면 성인 등급으로 발행돼요. 노출은 서버 정책에 따라 만 19세 이상 인증 이용자에게만
            허용되며, 목록·상세에서 블러 처리됩니다.
          </span>
        </div>
        {/* 19+ 등급은 서버 PostIn.is_adult로 실 전송. 실제 노출 활성화는 서버 ENABLE_ADULT_CONTENT
            플래그(base=False)가 통제하므로, 켜도 정책 사인 전까지는 노출되지 않는다(방어적). */}
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
        <Button className="flex-1" onClick={publish} disabled={publishPost.isPending || uploadImage.isPending}>
          발행하기
        </Button>
      </div>
    </div>
  );
}
