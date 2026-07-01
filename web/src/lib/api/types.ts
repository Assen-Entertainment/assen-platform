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
  type: MonetizableItemType;
  title: string;
  price: number;
  meta?: string;
  mediaUrl?: string;
}

export interface MembershipTier {
  id: string;
  name: string;
  price: number;
  period: string;
  benefits: string[];
  badge?: string;
  featured?: boolean;
}

export interface Paginated<T> {
  items: T[];
  nextCursor?: string | null;
}
