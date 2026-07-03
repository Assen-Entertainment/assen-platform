"use client";
import * as React from "react";
import {
  DataTable,
  type DataTableColumn,
  Badge,
  Button,
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
import {
  STUDIO_PRODUCTS,
  PRODUCT_STATUS_META,
  won,
  type StudioProduct,
  type ProductStatus,
} from "@/lib/studio-mock";
import { PRODUCT_TYPE_LABEL } from "@/lib/product-labels";
import type { MonetizableItemType } from "@/components/ui";

const FILTERS: { label: string; value: ProductStatus | "all" }[] = [
  { label: "전체", value: "all" },
  { label: "판매중", value: "selling" },
  { label: "품절", value: "soldout" },
  { label: "임시저장", value: "draft" },
];

const columns: DataTableColumn<StudioProduct>[] = [
  { key: "title", header: "상품명", render: (r) => <span className="line-clamp-1 text-on-surface">{r.title}</span> },
  { key: "type", header: "유형", render: (r) => PRODUCT_TYPE_LABEL[r.type] },
  { key: "price", header: "가격", align: "right", render: (r) => <span className="tabular-nums">{won(r.price)}</span> },
  { key: "sold", header: "판매", align: "right", render: (r) => <span className="tabular-nums">{r.sold.toLocaleString("ko-KR")}</span> },
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
];

/** Studio 상품 관리 — Figma Web-ManagementTable(191:281) / W3. DataTable + 상태 필터 + 새 상품 다이얼로그(UI). */
export default function StudioProductsPage() {
  const { toast } = useToast();
  const [filter, setFilter] = React.useState<ProductStatus | "all">("all");
  const [open, setOpen] = React.useState(false);
  // 등록 시 로컬 state에 행 append(settings/payments 데모 패턴). 실 저장은 게이트.
  const [products, setProducts] = React.useState<StudioProduct[]>(STUDIO_PRODUCTS);
  const [newTitle, setNewTitle] = React.useState("");
  const [newType, setNewType] = React.useState<MonetizableItemType>("goods");
  const [newPrice, setNewPrice] = React.useState("");

  const rows = React.useMemo(
    () => (filter === "all" ? products : products.filter((p) => p.status === filter)),
    [filter, products],
  );

  const onCreate = () => {
    // mock 등록 — 로컬 state에 임시저장 행 추가(실제 백엔드 저장 없음, 게이트).
    const title = newTitle.trim() || "새 상품";
    setProducts((prev) => [
      { id: `new-${Date.now()}`, type: newType, title, price: Number(newPrice) || 0, status: "draft", sold: 0, stock: null, updatedAt: "방금" },
      ...prev,
    ]);
    setNewTitle("");
    setNewType("goods");
    setNewPrice("");
    toast({ title: "상품이 등록되었어요", description: "새 상품이 목록에 추가되었습니다. (데모)" });
    setOpen(false);
  };

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-5">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-headline text-on-surface">상품 관리</h1>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>새 상품</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogTitle>새 상품 등록</DialogTitle>
            <DialogDescription>상품 정보를 입력하세요. (데모 — 실제 저장되지 않아요)</DialogDescription>
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
            <TextField label="가격 (원)" type="number" inputMode="numeric" placeholder="0" value={newPrice} onChange={(e) => setNewPrice(e.target.value)} />
            <TextArea label="설명" placeholder="상품 설명을 입력하세요." className="min-h-24" />
            <div className="mt-1 flex gap-2">
              <DialogClose asChild>
                <Button variant="outline" className="flex-1">
                  취소
                </Button>
              </DialogClose>
              <Button className="flex-1" onClick={onCreate}>
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

      <DataTable columns={columns} rows={rows} rowKey={(r) => r.id} caption="상품 목록" />
    </div>
  );
}
