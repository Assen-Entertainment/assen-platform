"use client";
import * as React from "react";
import {
  Card,
  CardBody,
  Button,
  Badge,
  Switch,
  TextField,
  Divider,
  SectionHeader,
} from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { STUDIO_TIERS, won, type StudioTier } from "@/lib/studio-mock";

/** Studio 멤버십 관리 — W3. 티어 목록 카드 + 편집 폼(이름/가격/혜택 편집, mock 저장). */
export default function StudioMembershipPage() {
  const { toast } = useToast();
  const [tiers, setTiers] = React.useState<StudioTier[]>(STUDIO_TIERS);
  const [editingId, setEditingId] = React.useState<string | null>(null);

  const editing = tiers.find((t) => t.id === editingId) ?? null;

  const saveTier = (next: StudioTier) => {
    setTiers((prev) => prev.map((t) => (t.id === next.id ? next : t)));
    setEditingId(null);
    // mock 저장 — 실제 반영 없음(게이트). 상태만 로컬 갱신.
    toast({ title: "티어가 저장되었어요", description: "변경 사항이 반영되었습니다. (데모)" });
  };

  const toggleActive = (id: string, active: boolean) => {
    setTiers((prev) => prev.map((t) => (t.id === id ? { ...t, active } : t)));
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5">
      <SectionHeader title="멤버십 관리" description="티어와 혜택을 관리하세요" />

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
                    {won(t.price)}/월 · 구독자 {t.subscribers.toLocaleString("ko-KR")}명
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

      {editing ? (
        <>
          <Divider />
          <TierEditForm key={editing.id} tier={editing} onSave={saveTier} onCancel={() => setEditingId(null)} />
        </>
      ) : null}
      <p className="text-center text-caption text-on-surface-variant">※ 데모 — 실제 멤버십 반영·정산 미연동(게이트)</p>
    </div>
  );
}

/** 티어 편집 폼 — 이름/가격/혜택 목록(추가·삭제·수정). 로컬 상태 → mock 저장. */
function TierEditForm({
  tier,
  onSave,
  onCancel,
}: {
  tier: StudioTier;
  onSave: (t: StudioTier) => void;
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
        <Button variant="outline" className="flex-1" onClick={onCancel}>
          취소
        </Button>
        <Button className="flex-1" onClick={submit}>
          저장
        </Button>
      </div>
    </section>
  );
}
