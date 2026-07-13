import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:assen_mobile/src/followers/follower.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Thrown when `GET /api/creators/{handle}/followers` returns 404 (unknown handle).
///
/// A typed marker so the 팔로워 screen shows a "크리에이터를 찾을 수 없어요" state rather
/// than the generic retry error — the endpoint 404s an unknown handle, keeping
/// parity with the profile read (no existence leak).
class FollowersCreatorNotFoundException implements Exception {
  /// Creates the not-found marker.
  const FollowersCreatorNotFoundException();

  @override
  String toString() => 'FollowersCreatorNotFoundException';
}

/// Fetches a creator's public followers list.
///
/// A thin repository over [Dio] owning `GET /api/creators/{handle}/followers` and
/// the JSON→model mapping. The endpoint is a public read (a follower's nickname
/// is already public), so there is no auth-required branch; a 404 becomes a
/// [FollowersCreatorNotFoundException]. When the generated `api_client` (P6)
/// lands this delegates to it instead of Dio.
class FollowersRepository {
  /// Creates a repository backed by [_dio].
  const FollowersRepository(this._dio);

  final Dio _dio;

  /// Loads [handle]'s followers via `GET /api/creators/{handle}/followers`.
  ///
  /// Maps the `FollowerPage` envelope (`{items, next_cursor}`) into a list of
  /// [Follower]s, newest first; only the first page is read here (cursor paging
  /// is a follow-up). The `items` array must be present (an empty array is the
  /// empty state); a missing key throws (an [ArgumentError] via [requireList]).
  Future<List<Follower>> fetchFollowers(String handle) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/creators/$handle/followers',
      );
      final body = response.data ?? const <String, dynamic>{};
      final items = requireList(body, 'items');
      return items
          .map((item) => Follower.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        throw const FollowersCreatorNotFoundException();
      }
      rethrow;
    }
  }
}

/// Provides the [FollowersRepository] bound to the [dioProvider].
///
/// Overridden with a fake in widget tests so the 팔로워 screen can render mock
/// followers (or the 404 branch) without a network.
final followersRepositoryProvider = Provider<FollowersRepository>(
  (ref) => FollowersRepository(ref.watch(dioProvider)),
);
