import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Thrown when `GET /api/creators/{handle}` returns 404 (unknown handle).
///
/// A typed marker (not a generic error) so the profile screen can render the
/// dedicated "없는 크리에이터" state instead of the generic retry error.
class CreatorNotFoundException implements Exception {
  /// Creates the not-found marker for [handle].
  const CreatorNotFoundException(this.handle);

  /// The handle that did not resolve.
  final String handle;

  @override
  String toString() => 'CreatorNotFoundException($handle)';
}

/// The follow state a follow/unfollow toggle resolves to: the server's truth.
///
/// A tiny record (not a model) carrying the two fields
/// `PUT|DELETE /api/creators/{handle}/follow` answers with
/// (`{following, followers}`), so the profile controller can reconcile its
/// optimistic flip against the authoritative follower count.
typedef FollowState = ({bool following, int followers});

/// Fetches a single creator profile from the backend.
///
/// A thin repository over [Dio] owning the endpoint path and the JSON→model
/// mapping so the controller/UI stay transport-agnostic. When the generated
/// `api_client` (P6) lands, this delegates to it instead of calling Dio.
class CreatorRepository {
  /// Creates a repository backed by [_dio].
  const CreatorRepository(this._dio);

  final Dio _dio;

  /// Loads the public creator profile for [handle].
  ///
  /// Calls `GET /api/creators/{handle}` and maps the `CreatorOut` body into a
  /// [Creator]. A 404 is translated into a [CreatorNotFoundException] so the
  /// screen shows the "unknown creator" state; other transport errors propagate
  /// to the generic error state.
  Future<Creator> fetchCreator(String handle) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/creators/${Uri.encodeComponent(handle)}',
      );
      return Creator.fromJson(response.data ?? const <String, dynamic>{});
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        throw CreatorNotFoundException(handle);
      }
      rethrow;
    }
  }

  /// Follows or unfollows a creator via
  /// `PUT`/`DELETE /api/creators/{handle}/follow`.
  ///
  /// [following] true sends the PUT (follow), false the DELETE (unfollow); both
  /// are idempotent server-side and answer `{following, followers}`, returned
  /// here as the authoritative [FollowState] the controller reconciles against.
  /// A 404 (an unknown handle) is translated into a [CreatorNotFoundException].
  Future<FollowState> setFollow(
    String handle, {
    required bool following,
  }) async {
    final path = '/api/creators/${Uri.encodeComponent(handle)}/follow';
    try {
      final response = following
          ? await _dio.put<Map<String, dynamic>>(path)
          : await _dio.delete<Map<String, dynamic>>(path);
      final body = response.data ?? const <String, dynamic>{};
      return (
        following: requireBool(body, 'following'),
        followers: requireInt(body, 'followers'),
      );
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        throw CreatorNotFoundException(handle);
      }
      rethrow;
    }
  }
}

/// Provides the [CreatorRepository] bound to the configured [dioProvider].
///
/// Overridden with a fake in widget tests so the profile screen can render mock
/// data without a network.
final creatorRepositoryProvider = Provider<CreatorRepository>(
  (ref) => CreatorRepository(ref.watch(dioProvider)),
);
