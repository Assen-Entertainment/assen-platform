import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { apiUpload } from "./index";

/**
 * 이미지 업로드(R12) 검증 — mock 폴백(USE_API=false·objectURL/플레이스홀더)과 실 경로
 * (USE_API=true → multipart FormData `file` 필드, JSON Content-Type 생략, {url} 반환,
 * 서버 {detail, code} → ApiError.code → apiErrorMessage 매핑). 실 경로는 NEXT_PUBLIC_API_URL을
 * stub한 뒤 모듈을 재로딩해 빌드타임 상수 USE_API를 뒤집는다(config/client/index 재평가).
 */

function mockJson(status: number, payload: unknown) {
  return vi.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(payload),
  })) as unknown as typeof fetch;
}

const pngFile = () => new File([new Uint8Array([0x89, 0x50, 0x4e, 0x47])], "shot.png", { type: "image/png" });

beforeEach(() => {
  // csrftoken 쿠키를 심어 /fan/csrf 프라이밍을 건너뛴다(단일 fetch 호출 보장).
  document.cookie = "csrftoken=testtok";
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("apiUpload — mock 폴백(USE_API=false)", () => {
  it("실 업로드 없이 미리보기 URL을 반환하고 fetch를 호출하지 않는다", async () => {
    const f = mockJson(201, { url: "/should/not/be/used" });
    vi.stubGlobal("fetch", f);

    const res = await apiUpload(pngFile());
    expect(typeof res.url).toBe("string");
    expect(res.url.length).toBeGreaterThan(0);
    expect((f as unknown as ReturnType<typeof vi.fn>).mock.calls).toHaveLength(0);
  });
});

describe("apiUpload — 실 경로(USE_API=true)", () => {
  it("multipart FormData(file)로 POST /uploads 전송·JSON Content-Type 없음·{url} 반환", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_API_URL", "/api");
    const f = mockJson(201, { url: "/media/uploads/abc.png" });
    vi.stubGlobal("fetch", f);

    const { apiUpload: liveUpload } = await import("./index");
    const res = await liveUpload(pngFile());
    expect(res).toEqual({ url: "/media/uploads/abc.png" });

    const [url, init] = (f as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(String(url)).toContain("/uploads");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    // multipart 바디 — boundary가 살도록 JSON Content-Type을 붙이지 않는다.
    expect(init.body instanceof FormData).toBe(true);
    expect((init.body as FormData).get("file")).toBeInstanceOf(File);
    expect(init.headers["Content-Type"]).toBeUndefined();
    expect(init.headers["X-CSRFToken"]).toBe("testtok");
  });

  it("서버 실패({detail, code})를 ApiError.code로 전파하고 apiErrorMessage가 문구로 매핑한다", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_API_URL", "/api");
    vi.stubGlobal("fetch", mockJson(415, { detail: "서버 상세", code: "UploadTypeUnsupported" }));

    const { apiUpload: liveUpload } = await import("./index");
    const { ApiError } = await import("./client");
    const { apiErrorMessage } = await import("./error-messages");

    let thrown: unknown;
    try {
      await liveUpload(pngFile());
    } catch (e) {
      thrown = e;
    }
    expect(thrown).toBeInstanceOf(ApiError);
    expect((thrown as InstanceType<typeof ApiError>).status).toBe(415);
    expect((thrown as InstanceType<typeof ApiError>).code).toBe("UploadTypeUnsupported");
    expect(apiErrorMessage(thrown)).toBe("이미지 파일(PNG·JPEG·WEBP·GIF)만 올릴 수 있어요.");
  });
});
