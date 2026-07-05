import type { MetadataRoute } from "next";
import { config } from "@/lib/config";
import { getCreatorsPage, getProductsPage } from "@/lib/api";
import type { Creator, Product, Page } from "@/lib/api";

/**
 * 동적 sitemap — 정적 표면 + 커서 순회로 수집한 크리에이터 핸들·상품 id.
 * getCreatorsPage/getProductsPage 를 nextCursor 소진까지 순회하되, 상한(페이지·항목)으로 방어한다
 * (실 API의 대량/무한 커서에도 sitemap 생성이 폭주하지 않도록). mock은 단일 페이지 → 1회 순회.
 */
const MAX_PAGES = 200;
const MAX_ITEMS = 10000;

/** 커서 페이지 함수를 nextCursor 소진(또는 상한)까지 순회해 전체 항목을 모은다. */
async function collectAll<T>(fetchPage: (cursor?: string) => Promise<Page<T>>): Promise<T[]> {
  const all: T[] = [];
  let cursor: string | undefined;
  for (let i = 0; i < MAX_PAGES && all.length < MAX_ITEMS; i++) {
    const page = await fetchPage(cursor);
    all.push(...page.items);
    if (!page.nextCursor) break;
    cursor = page.nextCursor;
  }
  return all.slice(0, MAX_ITEMS);
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [creators, products] = await Promise.all([
    collectAll<Creator>((c) => getCreatorsPage(c)),
    collectAll<Product>((c) => getProductsPage(undefined, c)),
  ]);

  const staticRoutes: MetadataRoute.Sitemap = ["", "/discovery", "/store", "/membership", "/feed"].map((path) => ({
    url: `${config.siteUrl}${path}`,
    changeFrequency: "daily",
    priority: path === "" ? 1 : 0.8,
  }));

  const creatorRoutes: MetadataRoute.Sitemap = creators.map((c) => ({
    url: `${config.siteUrl}/creator/${c.handle}`,
    changeFrequency: "weekly",
    priority: 0.7,
  }));

  const productRoutes: MetadataRoute.Sitemap = products.map((p) => ({
    url: `${config.siteUrl}/store/${p.id}`,
    changeFrequency: "weekly",
    priority: 0.6,
  }));

  return [...staticRoutes, ...creatorRoutes, ...productRoutes];
}
