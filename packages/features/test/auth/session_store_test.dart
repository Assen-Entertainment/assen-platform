import 'dart:convert';

import 'package:features/features.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('session codec', () {
    test('round-trips a session', () {
      final session = AuthSession(
        accessToken: 'mock-token',
        expiresAt: DateTime.utc(2026, 6, 12, 1, 2, 3),
      );

      expect(decodeSession(encodeSession(session)), session);
    });

    test('pins JSON keys for the landing handoff contract', () {
      // Protects the byte-level contract also written by landing/src/main.js.
      final raw = encodeSession(
        AuthSession(
          accessToken: 'mock-token',
          expiresAt: DateTime.utc(2026, 6, 12, 1, 2, 3),
        ),
      );

      final decoded = jsonDecode(raw) as Map<String, Object?>;
      expect(decoded.keys.toList(), ['accessToken', 'expiresAt']);
      expect(decoded, hasLength(2));
      expect(decoded['accessToken'], 'mock-token');
      expect(decoded['expiresAt'], '2026-06-12T01:02:03.000Z');
    });

    test('returns null for malformed input', () {
      expect(decodeSession('not json'), isNull);
      expect(decodeSession('{}'), isNull);
      expect(decodeSession('{"accessToken":"x"}'), isNull);
      expect(decodeSession('{"expiresAt":"2026-06-12T00:00:00.000Z"}'), isNull);
      expect(
        decodeSession('{"accessToken":1,"expiresAt":"2026-06-12T00:00:00Z"}'),
        isNull,
      );
      expect(
        decodeSession('{"accessToken":"x","expiresAt":"not a date"}'),
        isNull,
      );
    });
  });

  group('InMemorySessionStore', () {
    test('reads, writes, and clears', () {
      final store = InMemorySessionStore();
      final session = AuthSession(
        accessToken: 'seed',
        expiresAt: DateTime.utc(2026, 6, 12),
      );

      expect(store.read(), isNull);
      store.write(session);
      expect(store.read(), session);
      store.clear();
      expect(store.read(), isNull);
    });
  });

  group('MockAuthRepository store integration', () {
    test('hydrates currentSession from a seeded store', () {
      final store = InMemorySessionStore();
      final session = AuthSession(
        accessToken: 'seed',
        expiresAt: DateTime.utc(2026, 6, 12),
      );
      store.write(session);

      final repo = MockAuthRepository(store: store);

      expect(repo.currentSession, session);
    });

    test('signIn persists the minted session', () async {
      final store = InMemorySessionStore();
      final repo = MockAuthRepository(store: store);

      final session = await repo.signIn(identifier: 'fan', password: 'pw');

      expect(store.read(), session);
    });

    test('signOut clears the store', () async {
      final store = InMemorySessionStore();
      final repo = MockAuthRepository(store: store);

      await repo.signIn(identifier: 'fan', password: 'pw');
      await repo.signOut();

      expect(store.read(), isNull);
    });

    test('expireNow persists the expired session', () async {
      final store = InMemorySessionStore();
      final repo = MockAuthRepository(store: store);

      await repo.signIn(identifier: 'fan', password: 'pw');
      repo.expireNow();

      final stored = store.read();
      expect(stored, isNotNull);
      expect(stored!.isExpired(), isTrue);
    });
  });
}
