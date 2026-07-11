"use client";
import * as React from "react";
import {
  DataTable,
  type DataTableColumn,
  Badge,
  Button,
  Spinner,
  Switch,
  SegmentedControl,
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogClose,
  DialogTitle,
  DialogDescription,
  TextField,
  TextArea,
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui";
import { useToast } from "@/components/ui/use-toast";
import { PRODUCT_STATUS_META, won, type StudioProduct, type ProductStatus } from "@/lib/studio-mock";
import { PRODUCT_TYPE_LABEL } from "@/lib/product-labels";
import { ApiError, apiErrorMessage } from "@/lib/api";
import { useStudioProducts, useCreateProduct, useUpdateProduct, useDeleteProduct } from "@/lib/api/queries";
import type { MonetizableItemType } from "@/components/ui";

const FILTERS: { label: string; value: ProductStatus | "all" }[] = [
  { label: "전체", value: "all" },
  { label: "판매중", value: "selling" },
  { label: "품절", value: "soldout" },
  { label: "임시저장", value: "draft" },
];

const STATUS_OPTIONS: ProductStatus[] = ["selling", "soldout", "draft", "hidden"];

/** 실패 토스트 — 서버 error code→apiErrorMessage(detail 폴백). 401은 전역 세션 가드가 처리하므로 무시. */
function useApiErrorToast() {
  const { toast } = useToast();
  return (e: unknown, fallback: string) => {
    if (e instanceof ApiError && e.status === 401) return;
    toast({ title: fallback, description: apiErrorMessage(e) });
  };
}

/** Studio 상품 관리 — Figma Web-ManagementTable(191:281). 실 API(오너 스코프) CRUD + 상태 필터. */
export default function StudioProductsPage() {
  const { toast } = useToast();
  const onError = useApiErrorToast();
  const [filter, setFilter] = React.useState<ProductStatus | "all">("all");
  const [createOpen, setCreateOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<StudioProduct | null>(null);

  const { data, isLoading } = useStudioProducts();
  const createProduct = useCreateProduct();
  const updateProduct = useUpdateProduct();
  const deleteProduct = useDeleteProduct();

  const [newTitle, setNewTitle] = React.useState("");
  const [newType, setNewType] = React.useState<MonetizableItemType>("goods");
  const [newPrice, setNewPrice] = React.useState("");
  const [newDescription, setNewDescription] = React.useState("");
  // 무료 상품(ASS-297) — 켜면 가격 입력을 비활성·0원으로(서버 free-requires-zero-price 불변식 미러).
  const [newFree, setNewFree] = React.useState(false);

  const products = React.useMemo(() => data ?? [], [data]);
  const rows = React.useMemo(
    () => (filter === "all" ? products : products.filter((p) => p.status === filter)),
    [filter, products],
  );

  const resetCreate = () => {
    setNewTitle("");
    setNewType("goods");
    setNewPrice("");
    setNewDescription("");
    setNewFree(false);
  };

  const onCreate = () => {
    createProduct.mutate(
      {
        type: newType,
        title: newTitle.trim() || "새 상품",
        price: newFree ? 0 : Number(newPrice) || 0,
        description: newDescription.trim() || undefined,
        status: "draft",
        pricingKind: newFree ? "free" : "paid",
      },
      {
        onSuccess: () => {
          toast({ title: "상품이 등록되었어요", description: "임시저장 상태로 목록에 추가되었습니다." });
          resetCreate();
          setCreateOpen(false);
        },
        onError: (e) => onError(e, "등록하지 못했어요"),
      },
    );
  };

  const columns = React.useMemo<DataTableColumn<StudioProduct>[]>(
    () => [
      { key: "title", header: "상품명", render: (r) => <span className="line-clamp-1 text-on-surface">{r.title}</span> },
      { key: "type", header: "유형", render: (r) => PRODUCT_TYPE_LABEL[r.type] },
      { key: "price", header: "가격", align: "right", render: (r) => <span className="tabular-nums">{r.pricingKind === "free" ? "무료" : won(r.price)}</span> },
      {
        key: "sold",
        header: "판매",
        align: "right",
        // 집계 게이트 미도입: sold가 undefined면 "—"(집계 예정). 0을 실수치인 척 표기하지 않는다.
        render: (r) =>
          r.sold === undefined ? (
            <span className="text-on-surface-variant" title="집계 예정">
              —
            </span>
          ) : (
            <span className="tabular-nums">{r.sold.toLocaleString("ko-KR")}</span>
          ),
      },
      {
        key: "stock",
        header: "재고",
        align: "right",
        render: (r) => <span className="tabular-nums">{r.stock === null ? "무제한" : r.stock.toLocaleString("ko-KR")}</span>,
      },
      {
        key: "status",
        header: "상태",
        render: (r) => {
          const m = PRODUCT_STATUS_META[r.status];
          return <Badge variant={m.variant}>{m.label}</Badge>;
        },
      },
      {
        key: "actions",
        header: "관리",
        align: "right",
        render: (r) => (
          <Button variant="outline" size="sm" onClick={() => setEditing(r)}>
            편집
          </Button>
        ),
      },
    ],
    [],
  );

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-5">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-headline text-on-surface">상품 관리</h1>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button>새 상품</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogTitle>새 상품 등록</DialogTitle>
            <DialogDescription>상품 정보를 입력하세요. 임시저장 상태로 등록됩니다.</DialogDescription>
            <TextField label="상품명" placeholder="예: 아크릴 스탠드" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
            <div className="flex flex-col gap-1.5">
              <label htmlFor="new-product-type" className="text-label text-on-surface">
                유형
              </label>
              <Select value={newType} onValueChange={(v) => setNewType(v as MonetizableItemType)}>
                <SelectTrigger id="new-product-type" aria-label="상품 유형">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(PRODUCT_TYPE_LABEL) as MonetizableItemType[]).map((t) => (
                    <SelectItem key={t} value={t}>
                      {PRODUCT_TYPE_LABEL[t]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center justify-between gap-3 text-body-s text-on-surface">
              <span>무료 상품 (결제 없이 받기)</span>
              <Switch aria-label="무료 상품" checked={newFree} onCheckedChange={setNewFree} />
            </div>
            <TextField
              label="가격 (원)"
              type="number"
              inputMode="numeric"
              placeholder="0"
              value={newFree ? "0" : newPrice}
              onChange={(e) => setNewPrice(e.target.value)}
              disabled={newFree}
              helperText={newFree ? "무료 상품은 0원으로 고정돼요." : undefined}
            />
            <TextArea label="설명" placeholder="상품 설명을 입력하세요." className="min-h-24" value={newDescription} onChange={(e) => setNewDescription(e.target.value)} />
            <div className="mt-1 flex gap-2">
              <DialogClose asChild>
                <Button variant="outline" className="flex-1">
                  취소
                </Button>
              </DialogClose>
              <Button className="flex-1" onClick={onCreate} disabled={createProduct.isPending}>
                등록
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <SegmentedControl
        options={FILTERS.map((f) => ({ label: f.label, value: f.value }))}
        value={filter}
        onValueChange={(v) => setFilter(v as ProductStatus | "all")}
        className="self-start"
      />

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : (
        <DataTable columns={columns} rows={rows} rowKey={(r) => r.id} caption="상품 목록" />
      )}

      {/* 편집 다이얼로그 — 상품 수정 + 삭제(생성/편집/삭제 대칭). */}
      {editing ? (
        <ProductEditDialog
          key={editing.id}
          product={editing}
          saving={updateProduct.isPending}
          deleting={deleteProduct.isPending}
          onClose={() => setEditing(null)}
          onSave={(patch) =>
            updateProduct.mutate(
              { id: editing.id, ...patch },
              {
                onSuccess: () => {
                  toast({ title: "상품이 수정되었어요", description: "변경 사항이 저장되었습니다." });
                  setEditing(null);
                },
                onError: (e) => onError(e, "수정하지 못했어요"),
              },
            )
          }
          onDelete={() =>
            deleteProduct.mutate(editing.id, {
              onSuccess: () => {
                toast({ title: "상품이 삭제되었어요", description: "목록에서 제거되었습니다." });
                setEditing(null);
              },
              onError: (e) => onError(e, "삭제하지 못했어요"),
            })
          }
        />
      ) : null}
    </div>
  );
}

/** 상품 편집 다이얼로그 — 제목/유형/가격/상태/재고 수정 + 삭제. 로컬 상태 → 실 API. */
function ProductEditDialog({
  product,
  saving,
  deleting,
  onSave,
  onDelete,
  onClose,
}: {
  product: StudioProduct;
  saving: boolean;
  deleting: boolean;
  onSave: (patch: { type: MonetizableItemType; title: string; price: number; status: ProductStatus; stock: number | null; pricingKind: "paid" | "free" }) => void;
  onDelete: () => void;
  onClose: () => void;
}) {
  const [title, setTitle] = React.useState(product.title);
  const [type, setType] = React.useState<MonetizableItemType>(product.type);
  const [price, setPrice] = React.useState(String(product.price));
  const [status, setStatus] = React.useState<ProductStatus>(product.status);
  const [stock, setStock] = React.useState(product.stock === null ? "" : String(product.stock));
  // 무료 상품(ASS-297) — 켜면 가격 입력을 비활성·0원으로(서버 free-requires-zero-price 불변식 미러).
  const [free, setFree] = React.useState(product.pricingKind === "free");

  const submit = () =>
    onSave({
      type,
      title: title.trim() || product.title,
      price: free ? 0 : Number(price) || 0,
      status,
      // 빈 값 = 무제한(null). 그 외 숫자.
      stock: stock.trim() === "" ? null : Number(stock) || 0,
      pricingKind: free ? "free" : "paid",
    });

  return (
    <Dialog open onOpenChange={(o) => (!o ? onClose() : undefined)}>
      <DialogContent>
        <DialogTitle>상품 편집</DialogTitle>
        <DialogDescription>상품 정보를 수정하세요.</DialogDescription>
        <TextField label="상품명" value={title} onChange={(e) => setTitle(e.target.value)} />
        <div className="flex flex-col gap-1.5">
          <label htmlFor="edit-product-type" className="text-label text-on-surface">
            유형
          </label>
          <Select value={type} onValueChange={(v) => setType(v as MonetizableItemType)}>
            <SelectTrigger id="edit-product-type" aria-label="상품 유형">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(PRODUCT_TYPE_LABEL) as MonetizableItemType[]).map((t) => (
                <SelectItem key={t} value={t}>
                  {PRODUCT_TYPE_LABEL[t]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center justify-between gap-3 text-body-s text-on-surface">
          <span>무료 상품 (결제 없이 받기)</span>
          <Switch aria-label="무료 상품" checked={free} onCheckedChange={setFree} />
        </div>
        <div className="flex gap-3">
          <TextField
            label="가격 (원)"
            type="number"
            inputMode="numeric"
            value={free ? "0" : price}
            onChange={(e) => setPrice(e.target.value)}
            className="flex-1"
            disabled={free}
            helperText={free ? "무료 상품은 0원으로 고정돼요." : undefined}
          />
          <TextField
            label="재고"
            type="number"
            inputMode="numeric"
            placeholder="무제한"
            value={stock}
            onChange={(e) => setStock(e.target.value)}
            className="flex-1"
            helperText="비우면 무제한"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="edit-product-status" className="text-label text-on-surface">
            상태
          </label>
          <Select value={status} onValueChange={(v) => setStatus(v as ProductStatus)}>
            <SelectTrigger id="edit-product-status" aria-label="판매 상태">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((s) => (
                <SelectItem key={s} value={s}>
                  {PRODUCT_STATUS_META[s].label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="mt-1 flex gap-2">
          <Button
            variant="outline"
            className="border-error text-error hover:bg-error-container"
            onClick={onDelete}
            disabled={deleting}
          >
            삭제
          </Button>
          <div className="flex-1" />
          <DialogClose asChild>
            <Button variant="outline">취소</Button>
          </DialogClose>
          <Button onClick={submit} disabled={saving}>
            저장
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
