import type { MetadataRoute } from "next";
import { config } from "@/lib/config";
import { getCreators, getProducts } from "@/lib/api";

/**
 * 동적 sitemap — 정적 표면 + mock 크리에이터 핸들·상품 id를 포함.
 * 실 API 전환 시 lib/api 만 교체(핸들·id 소스 동일). /checkout·/api 는 robots 에서 제외.
 */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [creators, products] = await Promise.all([getCreators(), getProducts()]);

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
