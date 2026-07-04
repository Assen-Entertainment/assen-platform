"use client";
import * as React from "react";
import {
  Card,
  Button,
  Badge,
  Spinner,
  EmptyState,
  Divider,
  Checkbox,
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogClose,
  DialogTitle,
  DialogDescription,
  TextField,
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
  SafetyGuideNotice,
} from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { ApiError, apiErrorMessage } from "@/lib/api";
import {
  usePaymentMethods,
  useAddPaymentMethod,
  useRemovePaymentMethod,
  useSetPrimaryPaymentMethod,
} from "@/lib/api/queries";

// 브랜드 목록 — 서버로는 이 라벨만 전송(카드번호/CVC는 전송하지 않음, PCI).
const CARD_BRANDS = [
  "신한카드",
  "삼성카드",
  "현대카드",
  "KB국민카드",
  "롯데카드",
  "하나카드",
  "BC카드",
  "카카오페이",
  "토스",
  "페이코",
];

/**
 * 결제 수단 관리 — 실 API(오너 스코프). 목록 + 등록/삭제/기본 지정.
 * ★PCI(R4): 실 카드번호(PAN)/CVC는 서버로 절대 전송하지 않는다. 등록은 brand + mock PG 토큰만
 *   보내며(실 PG SDK가 클라에서 토큰화하는 자리), 카드 입력 위젯은 비활성 자리표시다.
 */
export default function PaymentsSettingsPage() {
  const { toast } = useToast();
  const { data, isLoading } = usePaymentMethods();
  const addMethod = useAddPaymentMethod();
  const removeMethod = useRemovePaymentMethod();
  const setPrimary = useSetPrimaryPaymentMethod();

  const [open, setOpen] = React.useState(false);
  const [brand, setBrand] = React.useState(CARD_BRANDS[0]);
  const [makePrimary, setMakePrimary] = React.useState(false);

  const methods = React.useMemo(() => data ?? [], [data]);

  const onError = (e: unknown, fallback: string) => {
    if (e instanceof ApiError && e.status === 401) return;
    // error code(PaymentCardInvalid·PaymentMethodNotFound 등) → apiErrorMessage(detail 표시 폴백).
    toast({ title: fallback, description: apiErrorMessage(e) });
  };

  const remove = (id: string) =>
    removeMethod.mutate(id, { onError: (e) => onError(e, "삭제하지 못했어요") });

  const makeDefault = (id: string) =>
    setPrimary.mutate(id, { onError: (e) => onError(e, "기본으로 설정하지 못했어요") });

  const add = () => {
    // brand + mock PG 토큰만 전송(raw 카드번호/CVC 미전송·PCI). 입력 위젯 값은 읽지 않는다.
    addMethod.mutate(
      { brand, makePrimary },
      {
        onSuccess: () => {
          toast({ title: "결제 수단이 등록되었어요", description: "새 결제 수단이 추가되었습니다." });
          setBrand(CARD_BRANDS[0]);
          setMakePrimary(false);
          setOpen(false);
        },
        onError: (e) => onError(e, "등록하지 못했어요"),
      },
    );
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
            <DialogDescription>카드사를 선택하세요. 카드 정보는 PG사에서 안전하게 처리됩니다.</DialogDescription>
            <SafetyGuideNotice title="안전한 결제">
              카드 정보는 PG사에서 암호화되어 처리되며 플랫폼에는 저장되지 않아요. 카드번호·CVC는 서버로 전송하지 않아요.
            </SafetyGuideNotice>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="pay-brand" className="text-label text-on-surface">
                카드사
              </label>
              <Select value={brand} onValueChange={setBrand}>
                <SelectTrigger id="pay-brand" aria-label="카드사">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CARD_BRANDS.map((b) => (
                    <SelectItem key={b} value={b}>
                      {b}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {/* 실 PG SDK 자리표시 — 비활성 mock 위젯(입력값은 서버로 전송되지 않음). */}
            <TextField label="카드 번호" placeholder="실 결제 연동 시 PG 위젯으로 입력" disabled helperText="PG 결제창에서 입력해요(데모 자리표시)." />
            <div className="flex gap-3">
              <TextField label="유효기간" placeholder="MM/YY" className="flex-1" disabled />
              <TextField label="CVC" placeholder="000" className="w-24" disabled />
            </div>
            <label className="flex items-center gap-2 text-body-s text-on-surface-variant">
              <Checkbox checked={makePrimary} onCheckedChange={(v) => setMakePrimary(v === true)} />
              기본 결제 수단으로 설정
            </label>
            <div className="mt-1 flex gap-2">
              <DialogClose asChild>
                <Button variant="outline" className="flex-1">
                  취소
                </Button>
              </DialogClose>
              <Button className="flex-1" onClick={add} disabled={addMethod.isPending}>
                등록
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : methods.length === 0 ? (
        <Card>
          <EmptyState
            title="등록된 결제 수단이 없어요"
            description="카드를 등록하면 더 빠르게 결제할 수 있어요."
            icon={<span className="text-2xl">💳</span>}
            action={<Button onClick={() => setOpen(true)}>카드 등록</Button>}
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
                    {m.isPrimary ? <Badge variant="primary">기본</Badge> : null}
                  </div>
                  <span className="text-caption text-on-surface-variant">•••• {m.last4}</span>
                </div>
                {!m.isPrimary ? (
                  <Button variant="ghost" size="sm" onClick={() => makeDefault(m.id)} disabled={setPrimary.isPending}>
                    기본으로
                  </Button>
                ) : null}
                <Button variant="ghost" size="sm" className="text-error" onClick={() => remove(m.id)} disabled={removeMethod.isPending}>
                  삭제
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
      <p className="text-center text-caption text-on-surface-variant">
        ※ 결제수단은 카드사·끝 4자리만 저장돼요. 실 카드번호·CVC는 저장·전송하지 않아요(PCI).
      </p>
    </div>
  );
}
