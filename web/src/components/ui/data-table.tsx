import * as React from "react";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";

/**
 * DataTable — Figma DS DataTable(214:101). Default/Empty/Loading 3상태.
 * 시맨틱 table(th scope=col / td) + overflow-x-auto 래핑(좁은 뷰포트 안전).
 * 스튜디오 정산·상품 관리 등 표 데이터에 사용. 무의존 · 제네릭.
 */
export interface DataTableColumn<T> {
  key: string;
  header: string;
  align?: "left" | "right" | "center";
  /** 셀 렌더러 — 미지정 시 row[key] 문자열. */
  render?: (row: T) => React.ReactNode;
  className?: string;
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  loading?: boolean;
  /** 로딩 스켈레톤 행 수(기본 4). */
  loadingRows?: number;
  /** 빈 상태 노드(미지정 시 기본 EmptyState). */
  empty?: React.ReactNode;
  /** 스크린리더용 표 설명. */
  caption?: string;
  className?: string;
  /** 행 클릭 핸들러 — 지정 시 행이 상호작용 가능(hover/포커스). */
  onRowClick?: (row: T) => void;
}

const alignClass = { left: "text-left", right: "text-right", center: "text-center" } as const;

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading,
  loadingRows = 4,
  empty,
  caption,
  className,
  onRowClick,
}: DataTableProps<T>) {
  return (
    <div className={cn("w-full overflow-x-auto rounded-lg border border-outline", className)}>
      <table className="w-full min-w-[32rem] border-collapse text-body-s">
        {caption ? <caption className="sr-only">{caption}</caption> : null}
        <thead>
          <tr className="border-b border-outline bg-surface-container-high">
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                className={cn("px-4 py-2.5 text-label font-medium text-on-surface-variant", alignClass[c.align ?? "left"])}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            Array.from({ length: loadingRows }).map((_, i) => (
              <tr key={`sk-${i}`} className="border-b border-outline last:border-b-0">
                {columns.map((c) => (
                  <td key={c.key} className="px-4 py-3">
                    <Skeleton className="h-4 w-full" />
                  </td>
                ))}
              </tr>
            ))
          ) : rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="p-0">
                {empty ?? <EmptyState title="표시할 항목이 없어요" description="새 항목이 등록되면 여기에 표시됩니다." />}
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr
                key={rowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={cn(
                  "border-b border-outline last:border-b-0",
                  onRowClick && "cursor-pointer transition-colors hover:bg-surface-container-high",
                )}
              >
                {columns.map((c) => (
                  <td
                    key={c.key}
                    className={cn("px-4 py-3 text-on-surface", alignClass[c.align ?? "left"], c.className)}
                  >
                    {c.render ? c.render(row) : String((row as Record<string, unknown>)[c.key] ?? "")}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
