/// Shared fetch-failure copy for the read surfaces.
///
/// Every screen's async error branch used to hard-code the same
/// "네트워크 상태를 확인하고 다시 시도해 주세요." line regardless of what actually failed.
/// [errorMessageFor] maps a caught error to a message that fits the failure —
/// a timeout, an offline connection, a 404/401/5xx response — so a retry hint
/// is honest about the cause. Unknown/non-Dio errors keep the original generic
/// network line, so a plain thrown [Exception] still reads sensibly.
library;

import 'package:dio/dio.dart';

/// Returns the user-facing message for a failed fetch [error].
///
/// [DioException]s are classified by transport type and (for a bad response)
/// HTTP status; anything else falls back to the generic network line. The
/// returned copy is a hint, not a diagnostic — it never leaks a status code,
/// URL, or any PII from the error.
String errorMessageFor(Object error) {
  if (error is! DioException) {
    return '네트워크 상태를 확인하고 다시 시도해 주세요.';
  }
  switch (error.type) {
    case DioExceptionType.connectionTimeout:
    case DioExceptionType.sendTimeout:
    case DioExceptionType.receiveTimeout:
    case DioExceptionType.transformTimeout:
      return '응답이 지연되고 있어요. 잠시 후 다시 시도해 주세요.';
    case DioExceptionType.connectionError:
      return '인터넷 연결이 불안정해요. 연결을 확인하고 다시 시도해 주세요.';
    case DioExceptionType.badCertificate:
      return '보안 연결에 문제가 생겼어요. 잠시 후 다시 시도해 주세요.';
    case DioExceptionType.badResponse:
      return _messageForStatus(error.response?.statusCode);
    case DioExceptionType.cancel:
    case DioExceptionType.unknown:
      return '네트워크 상태를 확인하고 다시 시도해 주세요.';
  }
}

/// Maps a bad-response HTTP [status] to its user-facing line.
String _messageForStatus(int? status) {
  if (status == null) {
    return '네트워크 상태를 확인하고 다시 시도해 주세요.';
  }
  if (status == 404) {
    return '요청한 정보를 찾지 못했어요.';
  }
  if (status == 401 || status == 403) {
    return '로그인이 필요하거나 접근 권한이 없어요.';
  }
  if (status >= 500) {
    return '서버에 일시적인 문제가 생겼어요. 잠시 후 다시 시도해 주세요.';
  }
  return '네트워크 상태를 확인하고 다시 시도해 주세요.';
}
