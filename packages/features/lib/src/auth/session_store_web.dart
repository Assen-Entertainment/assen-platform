import 'package:features/src/auth/auth_session.dart';
import 'package:features/src/auth/session_store.dart';
import 'package:web/web.dart' as web;

/// Creates the browser-backed session store for Flutter web.
SessionStore createPlatformSessionStore() => WebSessionStore();

/// Browser localStorage-backed store for the ASS-140 mock session bridge.
///
/// Expired sessions are returned as stored because expiry policy belongs to the
/// repository/router guard; the storage layer only preserves the handoff bytes.
class WebSessionStore implements SessionStore {
  @override
  AuthSession? read() {
    try {
      final raw = web.window.localStorage.getItem(assenSessionStorageKey);
      return raw == null ? null : decodeSession(raw);
      // 브라우저 스토리지 예외는 JS 기원이라 안정적인 Dart 예외 타입이 없어 storage 경계에서 의도적으로 전체를 잡는다.
    } on Object catch (_) {
      return null;
    }
  }

  @override
  void write(AuthSession session) {
    try {
      web.window.localStorage.setItem(
        assenSessionStorageKey,
        encodeSession(session),
      );
    } on Object catch (_) {
      // Storage can be unavailable in private browsing; auth still works in
      // memory for the current tab through MockAuthRepository.
    }
  }

  @override
  void clear() {
    try {
      web.window.localStorage.removeItem(assenSessionStorageKey);
    } on Object catch (_) {
      // Best-effort cleanup only; callers still clear in-memory state.
    }
  }
}
