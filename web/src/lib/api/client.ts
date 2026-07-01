import { config } from "@/lib/config";

/** API 오류 — status 보존. */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface ApiOptions extends RequestInit {
  token?: string;
}

/** 타입드 fetch 래퍼 — config.apiUrl 기준, Bearer 토큰, JSON. */
export async function apiFetch<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const { token, headers, ...rest } = opts;
  const res = await fetch(`${config.apiUrl}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });
  if (!res.ok) throw new ApiError(res.status, `API ${res.status}: ${path}`);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
