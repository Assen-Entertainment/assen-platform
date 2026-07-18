import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getProduct } from "@/lib/api";
import { config } from "@/lib/config";
import { JsonLd } from "@/components/json-ld";
import { ProductDetailView } from "./product-detail-view";

/** 상품 상세 — 동적 라우트(/store/[id]). 서버 fetch → 클라 뷰(initialData 하이드레이션). */
export default async function ProductDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const product = await getProduct(id);
  if (!product) notFound();
  // Product JSON-LD(#5a) — 실 데이터만(이름·설명·가격·재고 가용성). 리뷰/평점은 미보유 → 싣지 않는다(날조 금지).
  const soldOut = Boolean(product.soldOut) || product.stock === 0;
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.title,
    ...(product.description ? { description: product.description } : {}),
    ...(product.creatorName ? { brand: { "@type": "Brand", name: product.creatorName } } : {}),
    offers: {
      "@type": "Offer",
      price: product.price,
      priceCurrency: "KRW",
      availability: soldOut ? "https://schema.org/OutOfStock" : "https://schema.org/InStock",
      url: `${config.siteUrl}/store/${product.id}`,
    },
  };
  return (
    <>
      <JsonLd data={jsonLd} />
      <ProductDetailView product={product} />
    </>
  );
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const product = await getProduct(id);
  if (!product) return { title: "상품" };
  const description = product.description?.slice(0, 80) ?? product.meta;
  return {
    title: product.title,
    description,
    alternates: { canonical: `/store/${product.id}` },
    openGraph: { title: product.title, description },
  };
}
