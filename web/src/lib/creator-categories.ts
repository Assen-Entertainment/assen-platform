/**
 * 크리에이터 카테고리 정본 집합 — 서버 미러 `server/apps/creator/categories.py`
 * (`CREATOR_CATEGORIES`)와 **동기**. 두 리스트는 값·순서가 반드시 동일해야 한다(함께 변경).
 *
 * 콘텐츠형 창작 카테고리다. 굿즈(goods)는 상품유형(스토어 상품 필터)이라 크리에이터
 * 카테고리에서 의도적으로 제외한다. 저장 값은 이 배열의 원소(또는 "" = 미설정).
 */
export const CREATOR_CATEGORIES = [
  "일러스트",
  "뮤직",
  "버튜버",
  "게임",
  "사진",
  "코스프레",
  "글",
] as const;

export type CreatorCategory = (typeof CREATOR_CATEGORIES)[number];

/**
 * 표시 라벨 — 값과 다른 경우만 매핑(그 외는 값 그대로 표기). "글"은 discovery 카테고리
 * 아이콘 행(CATEGORY_ICONS)의 "글·소설" 라벨과 정합되게 표기한다.
 */
const CATEGORY_LABEL_OVERRIDES: Partial<Record<CreatorCategory, string>> = {
  글: "글·소설",
};

/** 카테고리 값 → 표시 라벨(미설정/알 수 없는 값은 그대로 반환). */
export function categoryLabel(value: string): string {
  return CATEGORY_LABEL_OVERRIDES[value as CreatorCategory] ?? value;
}
