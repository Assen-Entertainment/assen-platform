import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getProduct } from "@/lib/api";
import { ProductDetailView } from "./product-detail-view";

/** 상품 상세 — 동적 라우트(/store/[id]). 서버 fetch → 클라 뷰(initialData 하이드레이션). */
export default async function ProductDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const product = await getProduct(id);
  if (!product) notFound();
  return <ProductDetailView product={product} />;
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const product = await getProduct(id);
  if (!product) return { title: "상품" };
  const description = product.description?.slice(0, 80) ?? product.meta;
  return { title: product.title, description, openGraph: { title: product.title, description } };
}
