// Tests for SecureTokenStore against a mocked flutter_secure_storage channel:
// a save→read round-trip returns the pair, clear forgets it, a corrupt stored
// value reads as signed out (null, fail-closed), and — because the pair is
// persisted atomically under a single key — an interrupted write leaves the
// prior complete pair intact rather than a spliced old/new mix. No real
// keystore is touched.

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
  // When set, the next channel `write` throws (simulating a process kill /
  // channel error mid-write) and leaves the backing store untouched.
  late bool failNextWrite;

  setUp(() {
    backing = {};
    failNextWrite = false;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_channel, (call) async {
          final args = (call.arguments as Map).cast<String, dynamic>();
          switch (call.method) {
            case 'write':
              if (failNextWrite) {
                failNextWrite = false;
                throw Exception('secure storage write interrupted');
              }
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

  test('a corrupt stored value reads as signed out (fail-closed)', () async {
    // A garbled/non-JSON entry (e.g. an aborted write or keystore corruption)
    // is treated as no session rather than throwing into the session restore.
    backing['assen.auth.token_pair'] = 'not-json{';

    expect(await store.read(), isNull);
  });

  test('an interrupted write keeps the prior pair intact (atomic)', () async {
    // Seed a complete pair, then fail the next write mid-flight.
    await store.save(
      const AuthTokens(accessToken: 'old-a', refreshToken: 'old-r'),
    );
    failNextWrite = true;

    await expectLater(
      store.save(
        const AuthTokens(accessToken: 'new-a', refreshToken: 'new-r'),
      ),
      throwsA(anything),
    );

    // The single-key JSON design makes the write atomic: the next load sees the
    // prior *complete* pair, never a new-access + old-refresh splice.
    final read = await store.read();
    expect(read?.accessToken, 'old-a');
    expect(read?.refreshToken, 'old-r');
  });
}
