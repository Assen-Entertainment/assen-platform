import { createHmac } from "node:crypto";

/**
 * 서버 MockOtpSender(config/otp.py)와 동일한 결정적 OTP 파생.
 * normalize(+82 폴딩) 후 HMAC-SHA256의 앞 8 hex를 6자리 십진으로 축약한다.
 *
 * ⚠️ 시크릿("assen-dev-otp")은 서버 config/otp.py의 dev 기본 시크릿과 동기다 —
 *    서버가 바뀌면 여기도 함께 바꿔야 로그인 저니가 통과한다.
 *    (기존 scripts/integration-smoke.mjs의 otpFor와 동일 로직을 spec에서 재사용하기 위해 추출.)
 */
export function otpFor(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  const normalized = "+" + (digits.startsWith("0") ? "82" + digits.slice(1) : digits);
  const digest = createHmac("sha256", "assen-dev-otp").update(normalized).digest("hex");
  return String(parseInt(digest.slice(0, 8), 16) % 1_000_000).padStart(6, "0");
}
