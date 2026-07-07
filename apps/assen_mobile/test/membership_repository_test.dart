// Contract tests for the membership repository: fetchTiers parses the bare
// `list[TierOut]` array from GET /api/tiers, and a null/non-array body is a
// contract violation that throws (not a silently hidden section). A fake Dio
// adapter returns the JSON in-process, so nothing touches the network
// (CONSTRAINTS #24 — deterministic, offline).

import 'dart:typed_data';

import 'package:assen_mobile/src/membership/membership_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

/// A [Dio] adapter that answers every request with a fixed raw JSON [body],
/// so the parse path runs on an exact server payload without a socket.
class _RawJsonAdapter implements HttpClientAdapter {
  _RawJsonAdapter(this.body);

  final String body;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    return ResponseBody.fromString(
      body,
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

MembershipRepository _repoReturning(String body) => MembershipRepository(
  Dio(BaseOptions(baseUrl: 'http://localhost:8000'))
    ..httpClientAdapter = _RawJsonAdapter(body),
);

/// One `TierOut` row as the server serializes the bare array.
const _tierJson =
    '[{"id":"t1","name":"하츠코이","price":9900,"period":"월",'
    '"benefits":["비공개 포스트"],"badge":"VIP","featured":true,"sort_order":0}]';

void main() {
  test('fetchTiers parses the bare list[TierOut] array', () async {
    final tiers = await _repoReturning(_tierJson).fetchTiers('c1');
    expect(tiers, hasLength(1));
    expect(tiers.single.name, '하츠코이');
    expect(tiers.single.price, 9900);
  });

  test('fetchTiers returns an empty list for an empty array', () async {
    // A real `[]` is the only "no tiers" signal (the section then hides).
    expect(await _repoReturning('[]').fetchTiers('c1'), isEmpty);
  });

  test('fetchTiers throws on a null body (contract violation)', () async {
    await expectLater(
      _repoReturning('null').fetchTiers('c1'),
      throwsA(isA<ArgumentError>()),
    );
  });

  test('fetchTiers throws on a non-array body (contract violation)', () async {
    await expectLater(
      _repoReturning('{}').fetchTiers('c1'),
      throwsA(isA<ArgumentError>()),
    );
  });
}
