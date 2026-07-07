import { ImageResponse } from "next/og";

/**
 * 루트 OpenGraph 이미지(R5-W3 #5b) — 브랜드 뉴트럴 텍스트 카드(ImageResponse).
 * 페이지별 OG가 없을 때의 공용 공유 카드. 커스텀 폰트 미의존(Latin 워드마크)으로
 * 빌드/런타임 폰트 로딩 취약성을 피한다. 브랜드 그라디언트(--gradient-brand 정합).
 */
export const alt = "Assen — creator platform";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          backgroundImage: "linear-gradient(135deg, #5a4df0 0%, #8a5cf7 100%)",
          color: "#ffffff",
        }}
      >
        {/* 브랜드 마크(상승하는 A 모노그램) — 파비콘·Logo 컴포넌트와 형태 공유. */}
        <div
          style={{
            display: "flex",
            width: 104,
            height: 104,
            borderRadius: 28,
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(255,255,255,0.15)",
            border: "2px solid rgba(255,255,255,0.4)",
            marginBottom: 28,
          }}
        >
          <svg width="56" height="56" viewBox="0 0 32 32" fill="none" stroke="#ffffff" strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round">
            <path d="M10 23 L16 8.5 L22 23 M12.6 17.6 H19.4" />
          </svg>
        </div>
        <div style={{ fontSize: 132, fontWeight: 700, letterSpacing: -4 }}>Assen</div>
        <div style={{ marginTop: 16, fontSize: 34, opacity: 0.9 }}>creator platform</div>
      </div>
    ),
    { ...size },
  );
}
