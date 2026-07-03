import { getCreators, getProducts } from "@/lib/api";
import { SearchView } from "./search-view";

/** Search — `?q=` 초기값을 서버에서 읽어 뷰에 주입(TopBar 검색 submit 동기화). */
export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const [{ q }, creators, products] = await Promise.all([searchParams, getCreators(), getProducts()]);
  const initialQuery = (q ?? "").trim();
  // key: URL 질의 변경 시 뷰를 리마운트해 내부 초기 상태를 동기화.
  return <SearchView key={initialQuery} initialQuery={initialQuery} creators={creators} products={products} />;
}
