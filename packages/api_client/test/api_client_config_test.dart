import 'package:api_client/api_client.dart';
import 'package:test/test.dart';

void main() {
  group('ApiClientConfig', () {
    test('accepts an absolute https URL', () {
      final config = ApiClientConfig(baseUrl: 'https://api.assen.example');
      expect(config.baseUrl, 'https://api.assen.example');
    });

    test('rejects a relative URL', () {
      expect(
        () => ApiClientConfig(baseUrl: '/api'),
        throwsArgumentError,
      );
    });

    test('rejects a non-http scheme', () {
      expect(
        () => ApiClientConfig(baseUrl: 'ftp://example.com'),
        throwsArgumentError,
      );
    });

    test('rejects an http-prefixed but non-http scheme (ASS-296)', () {
      // startsWith('http') admitted these; scheme is now exact-matched.
      expect(
        () => ApiClientConfig(baseUrl: 'httpx://example.com'),
        throwsArgumentError,
      );
    });

    test('accepts a plain http URL', () {
      final config = ApiClientConfig(baseUrl: 'http://localhost:8000');
      expect(config.baseUrl, 'http://localhost:8000');
    });
  });
}
