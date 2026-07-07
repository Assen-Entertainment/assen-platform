// Tests for SecureTokenStore against a mocked flutter_secure_storage channel:
// a save→read round-trip returns the pair, clear forgets it, and a store
// missing either token reads as signed out (null). No real keystore is touched.

import 'package:assen_mobile/src/auth/token_store.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

const MethodChannel _channel = MethodChannel(
  'plugins.it_nomads.com/flutter_secure_storage',
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Map<String, String> backing;

  setUp(() {
    backing = {};
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_channel, (call) async {
          final args = (call.arguments as Map).cast<String, dynamic>();
          switch (call.method) {
            case 'write':
              backing[args['key'] as String] = args['value'] as String;
              return null;
            case 'read':
              return backing[args['key'] as String];
            case 'delete':
              backing.remove(args['key'] as String);
              return null;
            case 'containsKey':
              return backing.containsKey(args['key'] as String);
            default:
              return null;
          }
        });
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_channel, null);
  });

  const store = SecureTokenStore(FlutterSecureStorage());

  test('save then read round-trips the token pair', () async {
    await store.save(
      const AuthTokens(accessToken: 'a-token', refreshToken: 'r-token'),
    );

    final read = await store.read();
    expect(read?.accessToken, 'a-token');
    expect(read?.refreshToken, 'r-token');
  });

  test('read is null when no session is stored', () async {
    expect(await store.read(), isNull);
  });

  test('clear forgets a stored pair', () async {
    await store.save(
      const AuthTokens(accessToken: 'a-token', refreshToken: 'r-token'),
    );
    await store.clear();

    expect(await store.read(), isNull);
    expect(backing, isEmpty);
  });

  test('a half-written store reads as signed out (fail-closed)', () async {
    // Only the access token present (e.g. an interrupted write): treated as no
    // session rather than a malformed pair.
    backing['assen.auth.access_token'] = 'orphan';

    expect(await store.read(), isNull);
  });
}
