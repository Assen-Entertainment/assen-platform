import 'dart:convert';

import 'package:crypto/crypto.dart';

/// DEV/MOCK ONLY — derives the deterministic mock OTP for [phone].
///
/// Mirrors the backend `MockOtpSender.code_for` (HMAC-SHA256 of the
/// *normalized* phone under the repo's dev secret, first 8 hex digits mod
/// 1_000_000) so a
/// tester can complete the mock login without out-of-band SMS. The secret here
/// is the backend's non-production dev constant (`assen-dev-otp`); it backs the
/// mock only, which production disables (`ENABLE_MOCK_FAN_OTP=False`).
///
/// SECURITY: callers MUST gate this behind `!kReleaseMode` so it is never shown
/// in a shipped build — the login screen does. Returns null when the number is
/// too short to normalize, in which case no hint is shown.
String? devMockOtpCode(String phone) {
  final normalized = _normalizePhone(phone);
  if (normalized == null) return null;
  final digest = Hmac(
    sha256,
    utf8.encode('assen-dev-otp'),
  ).convert(utf8.encode(normalized));
  final prefix = digest.toString().substring(0, 8);
  final code = int.parse(prefix, radix: 16) % 1000000;
  return code.toString().padLeft(6, '0');
}

/// Canonicalises [phone] to the server's `normalize_phone` form (`+82…`).
///
/// Folds the Korean national trunk `0` onto `+82` and strips formatting so the
/// derived code keys on the same string the server hashes. Returns null for a
/// number shorter than the server's 8-digit floor.
String? _normalizePhone(String phone) {
  final hasPlus = phone.trim().startsWith('+');
  final digits = phone.replaceAll(RegExp('[^0-9]'), '');
  final String core;
  if (hasPlus) {
    core = digits;
  } else if (digits.startsWith('0')) {
    core = '82${digits.substring(1)}';
  } else {
    core = digits;
  }
  if (core.length < 8) return null;
  return '+$core';
}
