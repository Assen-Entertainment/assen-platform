"use client";
import * as React from "react";
import {
  Card,
  Button,
  Badge,
  EmptyState,
  Divider,
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogClose,
  DialogTitle,
  DialogDescription,
  TextField,
  SafetyGuideNotice,
} from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";

interface PayMethod {
  id: string;
  brand: string;
  last4: string;
  primary?: boolean;
}

const INITIAL: PayMethod[] = [
  { id: "m1", brand: "신한카드", last4: "4321", primary: true },
  { id: "m2", brand: "카카오페이", last4: "8890" },
];

/**
 * 결제 수단 관리 — W3. 목록 + 빈 상태 EmptyState + 카드 등록 다이얼로그(UI만).
 * ※실 결제수단 저장/PG 미연동(B4 게이트). 카드번호 등 민감정보 저장 금지 — 데모 표시만.
 */
export default function PaymentsSettingsPage() {
  const { toast } = useToast();
  const [methods, setMethods] = React.useState<PayMethod[]>(INITIAL);
  const [open, setOpen] = React.useState(false);

  const remove = (id: string) => setMethods((prev) => prev.filter((m) => m.id !== id));

  const addMock = () => {
    // mock 등록 — 실제 카드정보 저장 안 함(게이트). 표시용 더미만 추가.
    setMethods((prev) => [...prev, { id: `m${Date.now()}`, brand: "새 카드", last4: "0000" }]);
    toast({ title: "결제 수단이 등록되었어요", description: "새 결제 수단이 추가되었습니다. (데모)" });
    setOpen(false);
  };

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-headline text-on-surface">결제 수단</h1>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>카드 등록</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogTitle>결제 수단 등록</DialogTitle>
            <DialogDescription>카드 정보를 입력하세요. (데모 — 실제 저장되지 않아요)</DialogDescription>
            <SafetyGuideNotice title="안전한 결제">
              실제 서비스에서는 카드 정보가 PG사에서 암호화되어 처리되며 플랫폼에 저장되지 않아요.
            </SafetyGuideNotice>
            <TextField label="카드 번호" inputMode="numeric" placeholder="0000 0000 0000 0000" />
            <div className="flex gap-3">
              <TextField label="유효기간" placeholder="MM/YY" className="flex-1" />
              <TextField label="CVC" inputMode="numeric" placeholder="000" className="w-24" />
            </div>
            <div className="mt-1 flex gap-2">
              <DialogClose asChild>
                <Button variant="outline" className="flex-1">
                  취소
                </Button>
              </DialogClose>
              <Button className="flex-1" onClick={addMock}>
                등록
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {methods.length === 0 ? (
        <Card>
          <EmptyState
            title="등록된 결제 수단이 없어요"
            description="카드를 등록하면 더 빠르게 결제할 수 있어요."
            icon={<span className="text-2xl">💳</span>}
            action={
              <Button onClick={() => setOpen(true)}>카드 등록</Button>
            }
          />
        </Card>
      ) : (
        <div className="overflow-hidden rounded-lg border border-outline">
          {methods.map((m, i) => (
            <div key={m.id}>
              {i > 0 ? <Divider /> : null}
              <div className="flex items-center gap-3 px-4 py-3">
                <div className="flex min-w-0 flex-1 flex-col">
                  <div className="flex items-center gap-2">
                    <span className="text-body-l text-on-surface">{m.brand}</span>
                    {m.primary ? <Badge variant="primary">기본</Badge> : null}
                  </div>
                  <span className="text-caption text-on-surface-variant">•••• {m.last4}</span>
                </div>
                <Button variant="ghost" size="sm" className="text-error" onClick={() => remove(m.id)}>
                  삭제
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
      <p className="text-center text-caption text-on-surface-variant">※ 데모 — 실제 결제수단 저장·PG 미연동(게이트)</p>
    </div>
  );
}
