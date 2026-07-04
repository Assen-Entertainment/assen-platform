"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import {
  TextField,
  TextArea,
  Button,
  Divider,
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogClose,
  DialogTitle,
  DialogDescription,
  DisclaimerNotice,
} from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { useSession } from "@/lib/session";
import { ApiError, apiErrorMessage } from "@/lib/api";
import { useCreator, useUpdateMe, useUpdateStudioProfile } from "@/lib/api/queries";

/**
 * 계정 설정 — 닉네임은 PATCH /fan/me(실 저장·세션 무효화), 크리에이터 프로필(소개)은
 * PATCH /studio/profile로 분리. 계정 탈퇴는 소프트 게이트(하드 삭제/PII 파기는 운영 게이트) — mock 유지.
 */
export default function AccountSettingsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { user, logout } = useSession();
  const updateMe = useUpdateMe();
  const isCreator = user?.role === "creator";

  const [nickname, setNickname] = React.useState(user?.name ?? "");
  const [confirmText, setConfirmText] = React.useState("");

  // 세션은 마운트 후(useEffect)에 복원되므로 초기 user는 null → 닉네임이 비어 있을 때만 프리필.
  React.useEffect(() => {
    const n = user?.name;
    if (n) setNickname((cur) => (cur === "" ? n : cur));
  }, [user]);

  const saveNickname = () => {
    const value = nickname.trim();
    // 서버 계약: nickname 1~40자.
    if (value.length < 1 || value.length > 40) {
      toast({ title: "닉네임을 확인해 주세요", description: "1자 이상 40자 이하로 입력해 주세요." });
      return;
    }
    updateMe.mutate(value, {
      onSuccess: () => toast({ title: "저장되었어요", description: "닉네임이 업데이트되었습니다." }),
      onError: (e) => {
        if (e instanceof ApiError && e.status === 401) return;
        toast({ title: "저장하지 못했어요", description: apiErrorMessage(e) });
      },
    });
  };

  const onWithdraw = () => {
    // 소프트 게이트 — 세션만 정리 후 이동(하드 삭제/PII 파기는 운영 게이트).
    logout();
    toast({ title: "탈퇴 처리되었어요", description: "그동안 이용해 주셔서 감사합니다. (계정 삭제는 운영 게이트)" });
    router.push("/discovery");
  };

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5">
      <h1 className="text-headline text-on-surface">계정</h1>

      <section className="flex flex-col gap-4" aria-label="계정 정보">
        <TextField
          label="닉네임"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          placeholder="닉네임"
          maxLength={40}
        />
        <TextField label="이메일" type="email" placeholder="you@assen.kr" defaultValue="demo@assen.kr" disabled helperText="이메일 변경은 본인인증이 필요해요(게이트)." />
        <Button className="self-start" onClick={saveNickname} disabled={updateMe.isPending}>
          저장
        </Button>
      </section>

      {isCreator && user?.handle ? (
        <>
          <Divider />
          <CreatorProfileSection handle={user.handle} />
        </>
      ) : null}

      <Divider />

      <section className="flex flex-col gap-3" aria-label="위험 구역">
        <h2 className="text-title-l text-error">계정 탈퇴</h2>
        <p className="text-body-s text-on-surface-variant">
          탈퇴하면 프로필·구독·주문 내역이 삭제되며 되돌릴 수 없어요.
        </p>
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline" className="self-start border-error text-error hover:bg-error-container">
              계정 탈퇴
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogTitle>정말 탈퇴할까요?</DialogTitle>
            <DialogDescription>
              이 작업은 되돌릴 수 없어요. 계속하려면 아래에 <b className="text-on-surface">탈퇴</b>를 입력하세요.
            </DialogDescription>
            <DisclaimerNotice title="안내">계정 하드 삭제·개인정보 파기는 운영 게이트로 처리돼요. 여기서는 세션만 정리됩니다.</DisclaimerNotice>
            <TextField
              aria-label="탈퇴 확인 입력"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="탈퇴"
            />
            <div className="mt-1 flex gap-2">
              <DialogClose asChild>
                <Button variant="outline" className="flex-1">
                  취소
                </Button>
              </DialogClose>
              <Button
                className="flex-1 bg-error text-on-error hover:opacity-90"
                disabled={confirmText.trim() !== "탈퇴"}
                onClick={onWithdraw}
              >
                탈퇴하기
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </section>
    </div>
  );
}

/**
 * 크리에이터 프로필 섹션 — 현재 소개(bio)를 프리필한 뒤 PATCH /studio/profile로 저장.
 * (계정 폼과 분리 — 저장 시 빈 값으로 기존 소개를 덮어쓰지 않도록 현재 값을 불러온다.)
 */
function CreatorProfileSection({ handle }: { handle: string }) {
  const { toast } = useToast();
  const { data: creator } = useCreator(handle);
  const updateProfile = useUpdateStudioProfile();
  const [bio, setBio] = React.useState("");
  const [touched, setTouched] = React.useState(false);

  // 서버 소개를 최초 1회 프리필(사용자가 편집을 시작하면 덮어쓰지 않음).
  React.useEffect(() => {
    if (!touched && creator?.bio) setBio((cur) => (cur === "" ? creator.bio ?? "" : cur));
  }, [creator, touched]);

  const saveProfile = () => {
    updateProfile.mutate(
      { bio: bio.trim() },
      {
        onSuccess: () => toast({ title: "프로필이 저장되었어요", description: "크리에이터 소개가 업데이트되었습니다." }),
        onError: (e) => {
          if (e instanceof ApiError && e.status === 401) return;
          toast({ title: "저장하지 못했어요", description: apiErrorMessage(e) });
        },
      },
    );
  };

  return (
    <section className="flex flex-col gap-4" aria-label="크리에이터 프로필">
      <h2 className="text-title-l text-on-surface">크리에이터 프로필</h2>
      <TextArea
        label="소개"
        value={bio}
        onChange={(e) => {
          setTouched(true);
          setBio(e.target.value);
        }}
        placeholder="팬에게 보여줄 소개를 적어보세요."
        maxLength={160}
        showCount
      />
      <Button className="self-start" onClick={saveProfile} disabled={updateProfile.isPending}>
        프로필 저장
      </Button>
    </section>
  );
}
