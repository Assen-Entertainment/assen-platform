/**
 * JsonLd — schema.org 구조화 데이터 주입(R5-W3 #5a).
 * <script type="application/ld+json">로 직렬화. 서버 컴포넌트에서 실 데이터만 전달한다
 * (리뷰/평점 등 미보유 필드는 날조하지 않는다 — 존재하는 값만 스키마에 싣는다).
 */
export function JsonLd({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      // 신뢰 입력(서버 조립 객체) — XSS 방어로 '<'만 이스케이프.
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\\u003c") }}
    />
  );
}
