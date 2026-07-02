import type { MonetizableItemType } from "@/components/ui";

export interface Creator {
  id: string;
  name: string;
  handle: string;
  bio?: string;
  /** 크리에이터 시그니처 색(hex) — creatorAccent 주입. */
  accentColor?: string;
  avatarUrl?: string;
  coverUrl?: string;
  followers: number;
  posts?: number;
  verified?: boolean;
  category?: string;
  following?: boolean;
}

export interface Post {
  id: string;
  creatorId: string;
  creatorName: string;
  creatorMeta?: string;
  verified?: boolean;
  body?: string;
  mediaUrl?: string;
  likeCount: number;
  commentCount: number;
  liked?: boolean;
}

export interface Comment {
  id: string;
  postId: string;
  author: string;
  authorFallback?: string;
  body: string;
  /** 상대 시각 라벨(목업). 실 API 시 ISO → 포맷. */
  createdAt: string;
}

export interface Product {
  id: string;
  /** 소유 크리에이터(스토어 스코프). 전역 카탈로그 항목은 미지정. */
  creatorId?: string;
  type: MonetizableItemType;
  title: string;
  price: number;
  meta?: string;
  mediaUrl?: string;
}

export interface MembershipTier {
  id: string;
  /** 소유 크리에이터. 전역 목록은 미지정. */
  creatorId?: string;
  name: string;
  price: number;
  period: string;
  benefits: string[];
  badge?: string;
  featured?: boolean;
}

/** 커서 페이지 응답 — B2 wire 계약(snake_case). 마지막 페이지에서 next_cursor=null. */
export interface Paginated<T> {
  items: T[];
  next_cursor?: string | null;
}

/** /search 결과 (creators + products). */
export interface SearchResult {
  creators: Creator[];
  products: Product[];
}
