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

/**
 * 계정 설정 — W3. 프로필 정보 폼(UI) + 탈퇴 확인 Dialog(파괴적 확인 패턴).
 * ※실 계정/인증 미연동(B3 게이트). 저장·탈퇴는 mock.
 */
export default function AccountSettingsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { user, logout } = useSession();
  const [name, setName] = React.useState(user?.name ?? "");
  const [bio, setBio] = React.useState("");
  const [confirmText, setConfirmText] = React.useState("");

  // 세션은 마운트 후(useEffect)에 복원되므로 초기 user는 null → 이름이 비어 있을 때만 프리필.
  React.useEffect(() => {
    const n = user?.name;
    if (n) setName((cur) => (cur === "" ? n : cur));
  }, [user]);

  const onSave = () => {
    // mock 저장 — 실제 반영 없음(게이트).
    toast({ title: "저장되었어요", description: "프로필 정보가 업데이트되었습니다. (데모)" });
  };

  const onWithdraw = () => {
    // mock 탈퇴 — 세션만 정리 후 이동(실 계정 삭제 아님).
    logout();
    toast({ title: "탈퇴 처리되었어요", description: "그동안 이용해 주셔서 감사합니다. (데모)" });
    router.push("/discovery");
  };

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5">
      <h1 className="text-headline text-on-surface">계정</h1>

      <section className="flex flex-col gap-4" aria-label="프로필 정보">
        <TextField label="이름" value={name} onChange={(e) => setName(e.target.value)} placeholder="이름" />
        <TextField label="이메일" type="email" placeholder="you@assen.kr" defaultValue="demo@assen.kr" disabled helperText="이메일 변경은 본인인증이 필요해요(게이트)." />
        <TextArea label="소개" value={bio} onChange={(e) => setBio(e.target.value)} placeholder="팬에게 보여줄 소개를 적어보세요." maxLength={160} showCount />
        <Button className="self-start" onClick={onSave}>
          저장
        </Button>
      </section>

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
            <DisclaimerNotice title="데모 안내">실제 계정 삭제는 이루어지지 않아요(B3 게이트). mock 세션만 정리됩니다.</DisclaimerNotice>
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
