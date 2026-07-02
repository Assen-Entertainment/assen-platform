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
  });
}
