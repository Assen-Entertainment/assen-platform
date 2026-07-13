"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { TextField, Button } from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { useSession } from "@/lib/session";
import { ApiError } from "@/lib/api/client";

/** 핸들 규칙 — 서버(_HANDLE_VALIDATOR)와 동일: 영문 소문자·숫자·밑줄 2~32자. */
const HANDLE_RE = /^[a-z0-9_]{2,32}$/;

/**
 * 크리에이터 되기 — 셀프 개설(POST /studio/profile, D4). 핸들+이름을 정하면 크리에이터
 * 페이지가 열린다. "크리에이터"는 별도 role이 아니라 크리에이터 프로필 운영 여부(handle)로
 * 파생된다 — 개설 성공 후 /fan/me 재조회로 isCreator가 켜진다.
 */
export default function BecomeCreatorPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { user, mounted, becomeCreator } = useSession();
  const [handle, setHandle] = React.useState("");
  const [name, setName] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const normalized = handle.trim().toLowerCase();
  const handleValid = HANDLE_RE.test(normalized);
  const canSubmit = handleValid && name.trim().length > 0 && !busy;

  // 이미 크리에이터면 개설 화면 대신 스튜디오로 보낸다(중복 개설 방지).
  React.useEffect(() => {
    if (user?.isCreator) router.replace("/studio");
  }, [user?.isCreator, router]);

  const submit = async () => {
    if (!canSubmit) return;
    setBusy(true);
    setError(null);
    try {
      await becomeCreator({ handle: normalized, name: name.trim() });
      toast({ title: "크리에이터 페이지가 열렸어요", description: `@${normalized}` });
      router.push("/studio");
    } catch (e) {
      // 서버의 사용자 문구(핸들 중복·형식 등)를 그대로 노출, 없으면 폴백.
      setError(
        e instanceof ApiError && e.detail
          ? e.detail
          : "페이지 개설에 실패했어요. 잠시 후 다시 시도해 주세요.",
      );
      setBusy(false);
    }
  };

  if (mounted && !user) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-4 py-16 text-center">
        <h1 className="text-title-l text-on-surface">로그인이 필요해요</h1>
        <p className="text-body-s text-on-surface-variant">
          크리에이터 페이지를 열려면 먼저 로그인해 주세요.
        </p>
        <Button asChild>
          <Link href="/login?next=/become-creator">로그인</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-title-l text-on-surface">크리에이터 되기</h1>
        <p className="text-body-s text-on-surface-variant">
          핸들과 이름을 정하면 나만의 크리에이터 페이지가 열려요. 디지털 상품을
          등록해 판매할 수 있어요.
        </p>
      </div>

      <div className="flex flex-col gap-1">
        <TextField
          label="핸들"
          placeholder="my_handle"
          value={handle}
          onChange={(e) => setHandle(e.target.value)}
          maxLength={32}
        />
        {handle.length > 0 && !handleValid ? (
          <p className="text-caption text-error">
            소문자·숫자·밑줄(_) 2~32자로 입력해 주세요.
          </p>
        ) : handleValid ? (
          <p className="text-caption text-on-surface-variant">
            내 페이지 주소: /creator/{normalized}
          </p>
        ) : (
          <p className="text-caption text-on-surface-variant">
            영문 소문자·숫자·밑줄(_) 2~32자
          </p>
        )}
      </div>

      <TextField
        label="크리에이터 이름"
        placeholder="표시할 이름"
        value={name}
        onChange={(e) => setName(e.target.value)}
        maxLength={80}
      />

      {error ? <p className="text-body-s text-error">{error}</p> : null}

      <Button size="lg" className="w-full" disabled={!canSubmit} onClick={submit}>
        크리에이터 페이지 열기
      </Button>
    </div>
  );
}
