// Contract smoke tests for the discovery feed: the repository parses the real
// server `CreatorPage` envelope (`{items:[{CreatorOut}], next_cursor}`) from
// `GET /api/creators`, and the screen renders creators built from that shape.
// A fake Dio adapter returns the JSON in-process, so nothing touches the
// network (CONSTRAINTS #24 — deterministic, offline).

import 'dart:convert';
import 'dart:typed_data';

import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/discovery/discovery_repository.dart';
import 'package:assen_mobile/src/discovery/discovery_screen.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A [Dio] adapter that answers every request with a fixed JSON [payload],
/// standing in for the backend so the parse path runs without a socket.
class _EnvelopeAdapter implements HttpClientAdapter {
  _EnvelopeAdapter(this.payload);

  final Map<String, dynamic> payload;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    return ResponseBody.fromString(
      jsonEncode(payload),
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

Dio _dioReturning(Map<String, dynamic> payload) =>
    Dio(BaseOptions(baseUrl: 'http://localhost:8000'))
      ..httpClientAdapter = _EnvelopeAdapter(payload);

/// A repository stand-in that unwraps a server `CreatorPage` envelope the same
/// way [DiscoveryRepository] does, so the screen renders server-shaped rows
/// deterministically (a completed future, no network timing).
class _EnvelopeRepository implements DiscoveryRepository {
  _EnvelopeRepository(this.envelope);

  final Map<String, dynamic> envelope;

  @override
  Future<List<Creator>> fetchCreators() async {
    final items = envelope['items'] as List<dynamic>? ?? const <dynamic>[];
    return items
        .map((item) => Creator.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}

/// One full `CreatorOut` row as the server serializes it.
Map<String, dynamic> _creatorRow({
  Object id = 'a1b2',
  String handle = 'mio',
  String name = '미오',
  String category = '버추얼',
  String avatarUrl = 'https://cdn.example/mio.png',
}) => {
  'id': id,
  'handle': handle,
  'name': name,
  'bio': '',
  'accent_color': '#FF88AA',
  'avatar_url': avatarUrl,
  'cover_url': '',
  'category': category,
  'verified': true,
  'followers': 12,
  'posts': 3,
  'following': false,
  'blocked': false,
};

void main() {
  test('fetchCreators parses the CreatorPage envelope into creators', () async {
    final repo = DiscoveryRepository(
      _dioReturning({
        'items': [_creatorRow()],
        'next_cursor': null,
      }),
    );

    final creators = await repo.fetchCreators();

    expect(creators, hasLength(1));
    expect(creators.first.id, 'a1b2');
    expect(creators.first.handle, 'mio');
    expect(creators.first.displayName, '미오');
    expect(creators.first.category, '버추얼');
    expect(creators.first.avatarUrl, 'https://cdn.example/mio.png');
  });

  test(
    'fetchCreators coerces a numeric id and drops empty descriptors',
    () async {
      final repo = DiscoveryRepository(
        _dioReturning({
          'items': [
            _creatorRow(id: 42, name: '', category: '', avatarUrl: ''),
          ],
          'next_cursor': 'eyJoIjoibWlvIn0',
        }),
      );

      final creators = await repo.fetchCreators();

      expect(creators.first.id, '42');
      // Empty name falls back to the handle; empty category/avatar become null.
      expect(creators.first.displayName, 'mio');
      expect(creators.first.category, isNull);
      expect(creators.first.avatarUrl, isNull);
    },
  );

  test('a missing items array is treated as an empty feed', () async {
    final repo = DiscoveryRepository(_dioReturning({'next_cursor': null}));

    expect(await repo.fetchCreators(), isEmpty);
  });

  testWidgets('discovery renders creators parsed from the server envelope', (
    tester,
  ) async {
    // Feed data uses the real server envelope shape; empty avatar_url avoids a
    // NetworkImage fetch in the test.
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          discoveryRepositoryProvider.overrideWithValue(
            _EnvelopeRepository({
              'items': [_creatorRow(avatarUrl: '')],
              'next_cursor': null,
            }),
          ),
        ],
        child: MaterialApp(
          theme: AssenTheme.light(),
          home: const DiscoveryScreen(),
        ),
      ),
    );
    // First frame is the loading skeleton; a second pump lets the resolved
    // future rebuild the list.
    await tester.pump();
    await tester.pump();

    expect(find.text('미오'), findsOneWidget);
    expect(find.text('@mio · 버추얼'), findsOneWidget);
  });
}
