import 'package:assen_mobile/src/common/error_message.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

DioException _dio(DioExceptionType type, {int? status}) => DioException(
  requestOptions: RequestOptions(path: '/creators'),
  type: type,
  response: status == null
      ? null
      : Response<void>(
          requestOptions: RequestOptions(path: '/creators'),
          statusCode: status,
        ),
);

void main() {
  group('errorMessageFor', () {
    test('non-Dio errors fall back to the generic network line', () {
      expect(errorMessageFor(Exception('boom')), contains('네트워크 상태'));
      expect(errorMessageFor('a plain string'), contains('네트워크 상태'));
    });

    test('every timeout type maps to the delayed-response line', () {
      for (final t in const [
        DioExceptionType.connectionTimeout,
        DioExceptionType.sendTimeout,
        DioExceptionType.receiveTimeout,
        DioExceptionType.transformTimeout,
      ]) {
        expect(errorMessageFor(_dio(t)), contains('지연'), reason: '$t');
      }
    });

    test('connection error maps to the offline/unstable line', () {
      expect(
        errorMessageFor(_dio(DioExceptionType.connectionError)),
        contains('연결'),
      );
    });

    test('bad certificate maps to the secure-connection line', () {
      expect(
        errorMessageFor(_dio(DioExceptionType.badCertificate)),
        contains('보안'),
      );
    });

    test('bad response maps by HTTP status', () {
      expect(
        errorMessageFor(_dio(DioExceptionType.badResponse, status: 404)),
        contains('찾지 못'),
      );
      expect(
        errorMessageFor(_dio(DioExceptionType.badResponse, status: 401)),
        contains('로그인'),
      );
      expect(
        errorMessageFor(_dio(DioExceptionType.badResponse, status: 403)),
        contains('로그인'),
      );
      expect(
        errorMessageFor(_dio(DioExceptionType.badResponse, status: 500)),
        contains('서버'),
      );
      expect(
        errorMessageFor(_dio(DioExceptionType.badResponse, status: 503)),
        contains('서버'),
      );
      // A bad response with no status falls back to the generic line.
      expect(
        errorMessageFor(_dio(DioExceptionType.badResponse)),
        contains('네트워크 상태'),
      );
    });

    test('cancel/unknown keep the generic network line', () {
      expect(
        errorMessageFor(_dio(DioExceptionType.cancel)),
        contains('네트워크 상태'),
      );
      expect(
        errorMessageFor(_dio(DioExceptionType.unknown)),
        contains('네트워크 상태'),
      );
    });

    test('the copy never leaks a status code, path, or PII', () {
      final msg = errorMessageFor(
        _dio(DioExceptionType.badResponse, status: 404),
      );
      expect(msg, isNot(contains('404')));
      expect(msg, isNot(contains('/creators')));
    });
  });
}
