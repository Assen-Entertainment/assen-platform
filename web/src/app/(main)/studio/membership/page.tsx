"use client";
import * as React from "react";
import {
  Card,
  CardBody,
  Button,
  Badge,
  Switch,
  Spinner,
  TextField,
  TextArea,
  Divider,
  SectionHeader,
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogClose,
  DialogTitle,
  DialogDescription,
} from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { won, type StudioTier } from "@/lib/studio-mock";
import { ApiError } from "@/lib/api";
import { useStudioTiers, useCreateTier, useUpdateTier, useDeleteTier } from "@/lib/api/queries";

/** 실패 토스트 — ApiError.detail 우선(401은 전역 세션 가드가 처리). */
function useApiErrorToast() {
  const { toast } = useToast();
  return (e: unknown, fallback: string) => {
    if (e instanceof ApiError && e.status === 401) return;
    const description = e instanceof ApiError && e.detail ? e.detail : "잠시 후 다시 시도해 주세요.";
    toast({ title: fallback, description });
  };
}

/** Studio 멤버십 관리 — 실 API(오너 스코프) 티어 CRUD. 목록 + 생성/편집/삭제 대칭. */
export default function StudioMembershipPage() {
  const { toast } = useToast();
  const onError = useApiErrorToast();
  const { data, isLoading } = useStudioTiers();
  const createTier = useCreateTier();
  const updateTier = useUpdateTier();
  const deleteTier = useDeleteTier();

  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [createOpen, setCreateOpen] = React.useState(false);

  const tiers = React.useMemo(() => data ?? [], [data]);
  const editing = tiers.find((t) => t.id === editingId) ?? null;

  const saveTier = (next: StudioTier) => {
    updateTier.mutate(
      { id: next.id, name: next.name, price: next.price, benefits: next.benefits },
      {
        onSuccess: () => {
          setEditingId(null);
          toast({ title: "티어가 저장되었어요", description: "변경 사항이 반영되었습니다." });
        },
        onError: (e) => onError(e, "저장하지 못했어요"),
      },
    );
  };

  const toggleActive = (id: string, active: boolean) => {
    updateTier.mutate({ id, active }, { onError: (e) => onError(e, "상태를 바꾸지 못했어요") });
  };

  const removeTier = (id: string) => {
    deleteTier.mutate(id, {
      onSuccess: () => {
        setEditingId(null);
        toast({ title: "티어가 삭제되었어요", description: "목록에서 제거되었습니다." });
      },
      onError: (e) => onError(e, "삭제하지 못했어요"),
    });
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5">
      <div className="flex items-center justify-between gap-3">
        <SectionHeader title="멤버십 관리" description="티어와 혜택을 관리하세요" />
        <TierCreateDialog
          open={createOpen}
          onOpenChange={setCreateOpen}
          pending={createTier.isPending}
          onCreate={(input) =>
            createTier.mutate(input, {
              onSuccess: () => {
                toast({ title: "티어가 추가되었어요", description: "새 멤버십 티어가 생성되었습니다." });
                setCreateOpen(false);
              },
              onError: (e) => onError(e, "추가하지 못했어요"),
            })
          }
        />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {tiers.map((t) => (
            <Card key={t.id}>
              <CardBody className="gap-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 flex-col gap-0.5">
                    <div className="flex items-center gap-2">
                      <h2 className="text-title-l text-on-surface">{t.name}</h2>
                      <Badge variant={t.active ? "success" : "neutral"}>{t.active ? "활성" : "비활성"}</Badge>
                    </div>
                    <span className="text-body-s text-on-surface-variant">
                      {won(t.price)}/월 · 구독자{" "}
                      {/* 집계 게이트 미도입: undefined면 "—"(집계 예정). 0/날조 수치 노출 금지. */}
                      {t.subscribers === undefined ? (
                        <span title="집계 예정">—</span>
                      ) : (
                        `${t.subscribers.toLocaleString("ko-KR")}명`
                      )}
                    </span>
                  </div>
                  <Switch
                    aria-label={`${t.name} 활성화`}
                    checked={t.active}
                    onCheckedChange={(v) => toggleActive(t.id, v)}
                  />
                </div>
                <ul className="flex flex-col gap-1">
                  {t.benefits.map((b, i) => (
                    <li key={`${b}-${i}`} className="flex items-center gap-2 text-body-s text-on-surface-variant">
                      <span aria-hidden className="text-primary">
                        ✓
                      </span>
                      {b}
                    </li>
                  ))}
                </ul>
                <Button variant="outline" size="sm" className="self-start" onClick={() => setEditingId(t.id)}>
                  편집
                </Button>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {editing ? (
        <>
          <Divider />
          <TierEditForm
            key={editing.id}
            tier={editing}
            saving={updateTier.isPending}
            deleting={deleteTier.isPending}
            onSave={saveTier}
            onDelete={() => removeTier(editing.id)}
            onCancel={() => setEditingId(null)}
          />
        </>
      ) : null}
    </div>
  );
}

/** 티어 생성 다이얼로그 — 이름/가격/혜택(줄 단위). 실 API 생성. */
function TierCreateDialog({
  open,
  onOpenChange,
  pending,
  onCreate,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  pending: boolean;
  onCreate: (input: { name: string; price: number; benefits: string[] }) => void;
}) {
  const [name, setName] = React.useState("");
  const [price, setPrice] = React.useState("");
  const [benefits, setBenefits] = React.useState("");

  // 다이얼로그를 닫을 때 입력 초기화.
  React.useEffect(() => {
    if (!open) {
      setName("");
      setPrice("");
      setBenefits("");
    }
  }, [open]);

  const submit = () =>
    onCreate({
      name: name.trim() || "새 티어",
      price: Number(price) || 0,
      benefits: benefits
        .split("\n")
        .map((b) => b.trim())
        .filter(Boolean),
    });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button>새 티어</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle>새 티어 만들기</DialogTitle>
        <DialogDescription>멤버십 티어 정보를 입력하세요.</DialogDescription>
        <TextField label="티어 이름" placeholder="예: 스탠다드" value={name} onChange={(e) => setName(e.target.value)} />
        <TextField label="월 가격 (원)" type="number" inputMode="numeric" placeholder="0" value={price} onChange={(e) => setPrice(e.target.value)} />
        <TextArea
          label="혜택 (한 줄에 하나씩)"
          placeholder={"멤버 전용 포스트\n월 1회 라이브"}
          className="min-h-24"
          value={benefits}
          onChange={(e) => setBenefits(e.target.value)}
        />
        <div className="mt-1 flex gap-2">
          <DialogClose asChild>
            <Button variant="outline" className="flex-1">
              취소
            </Button>
          </DialogClose>
          <Button className="flex-1" onClick={submit} disabled={pending}>
            만들기
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/** 티어 편집 폼 — 이름/가격/혜택 목록(추가·삭제·수정) + 티어 삭제. 로컬 상태 → 실 API. */
function TierEditForm({
  tier,
  saving,
  deleting,
  onSave,
  onDelete,
  onCancel,
}: {
  tier: StudioTier;
  saving: boolean;
  deleting: boolean;
  onSave: (t: StudioTier) => void;
  onDelete: () => void;
  onCancel: () => void;
}) {
  // 혜택 항목에 안정적 id를 부여 → 추가/삭제/수정 시 index 키 재사용 버그 방지.
  const seq = React.useRef(0);
  const [name, setName] = React.useState(tier.name);
  const [price, setPrice] = React.useState(String(tier.price));
  const [benefits, setBenefits] = React.useState<{ id: string; text: string }[]>(
    () => tier.benefits.map((text) => ({ id: `b${seq.current++}`, text })),
  );

  const updateBenefit = (id: string, v: string) =>
    setBenefits((prev) => prev.map((b) => (b.id === id ? { ...b, text: v } : b)));
  const addBenefit = () => setBenefits((prev) => [...prev, { id: `b${seq.current++}`, text: "" }]);
  const removeBenefit = (id: string) => setBenefits((prev) => prev.filter((b) => b.id !== id));

  const submit = () => {
    onSave({
      ...tier,
      name: name.trim() || tier.name,
      price: Number(price) || 0,
      benefits: benefits.map((b) => b.text.trim()).filter(Boolean),
    });
  };

  return (
    <section className="flex flex-col gap-4 rounded-lg border border-outline bg-surface p-5" aria-label="티어 편집">
      <h2 className="text-title-l text-on-surface">티어 편집 — {tier.name}</h2>
      <TextField label="티어 이름" value={name} onChange={(e) => setName(e.target.value)} />
      <TextField
        label="월 가격 (원)"
        type="number"
        inputMode="numeric"
        value={price}
        onChange={(e) => setPrice(e.target.value)}
      />
      <div className="flex flex-col gap-2">
        <span className="text-label text-on-surface">혜택</span>
        {benefits.map((b, i) => (
          <div key={b.id} className="flex items-center gap-2">
            <TextField
              aria-label={`혜택 ${i + 1}`}
              value={b.text}
              onChange={(e) => updateBenefit(b.id, e.target.value)}
              placeholder="혜택 내용"
              className="flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label={`혜택 ${i + 1} 삭제`}
              onClick={() => removeBenefit(b.id)}
            >
              ✕
            </Button>
          </div>
        ))}
        <Button type="button" variant="outline" size="sm" className="self-start" onClick={addBenefit}>
          + 혜택 추가
        </Button>
      </div>
      <div className="flex gap-2">
        <Button
          variant="outline"
          className="border-error text-error hover:bg-error-container"
          onClick={onDelete}
          disabled={deleting}
        >
          삭제
        </Button>
        <div className="flex-1" />
        <Button variant="outline" onClick={onCancel}>
          취소
        </Button>
        <Button onClick={submit} disabled={saving}>
          저장
        </Button>
      </div>
    </section>
  );
}
