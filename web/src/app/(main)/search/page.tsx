import { getCreators, getProducts } from "@/lib/api";
import { SearchView } from "./search-view";

export default async function SearchPage() {
  const [creators, products] = await Promise.all([getCreators(), getProducts()]);
  return <SearchView creators={creators} products={products} />;
}
