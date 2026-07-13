import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:assen_mobile/src/post/post.dart';
import 'package:assen_mobile/src/studio/studio_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Fetches the signed-in creator owner's own posts (management view).
///
/// A thin repository over [Dio] owning `GET /api/studio/posts` and the JSON→model
/// mapping. Unlike the public feed this includes the owner's 19+ posts. Reuses
/// the shared [Post] model and the studio auth markers: a 401 becomes a
/// [StudioAuthRequiredException] (signed out) and a 403 a
/// [StudioOwnerRequiredException] (signed-in non-owner). Read-only — the
/// composer/edit/delete are follow-up. When `api_client` (P6) lands this
/// delegates to it instead of Dio.
class StudioPostsRepository {
  /// Creates a repository backed by [_dio].
  const StudioPostsRepository(this._dio);

  final Dio _dio;

  /// Loads the owner's posts via `GET /api/studio/posts` (owner auth).
  ///
  /// Maps the `PostPage` envelope (`{items, next_cursor}`) into a list of
  /// [Post]s, newest first; only the first page is read (cursor paging is a
  /// follow-up). The `items` array must be present (an empty array is the empty
  /// state); a missing key throws (an [ArgumentError] via [requireList]).
  Future<List<Post>> fetchPosts() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/studio/posts',
      );
      final body = response.data ?? const <String, dynamic>{};
      final items = requireList(body, 'items');
      return items
          .map((item) => Post.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (error) {
      final status = error.response?.statusCode;
      if (status == 401) throw const StudioAuthRequiredException();
      if (status == 403) throw const StudioOwnerRequiredException();
      rethrow;
    }
  }
}

/// Provides the [StudioPostsRepository] bound to the [dioProvider].
///
/// Overridden with a fake in widget tests so the 게시물 관리 screen can render mock
/// posts (or the 401/403 branches) without a network.
final studioPostsRepositoryProvider = Provider<StudioPostsRepository>(
  (ref) => StudioPostsRepository(ref.watch(dioProvider)),
);
