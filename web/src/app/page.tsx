import { redirect } from "next/navigation";

/**
 * 루트 진입(P0) — 사이트 첫인상은 디스커버리. 기존 "웹 디자인시스템 미리보기" 인덱스는
 * /design-system(내부용·noindex)으로 이전했다.
 */
export default function RootPage() {
  redirect("/discovery");
}
