import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:assen_mobile/src/post/post.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Fetches the global (most-recent) post feed from the backend.
///
/// A thin repository over [Dio] owning the endpoint path and the JSON→model
/// mapping so the controller/UI stay transport-agnostic. When the generated
/// `api_client` (P6) lands, this delegates to it instead of calling Dio.
class FeedRepository {
  /// Creates a repository backed by [_dio].
  const FeedRepository(this._dio);

  final Dio _dio;

  /// Loads the global feed via `GET /api/feed`.
  ///
  /// Maps the `PostPage` envelope (`{items, next_cursor}`) into a list of
  /// [Post]s, newest first; only the first page is read here (cursor
  /// paging is a follow-up). The envelope is parsed strictly: the `items`
  /// array must be
  /// present (an empty array is the empty feed), but a *missing* key is a
  /// contract violation and throws (an [ArgumentError] via [requireList])
  /// rather than silently showing an empty feed — matching the search/notifications
  /// envelopes.
  Future<List<Post>> fetchFeed() async {
    final response = await _dio.get<Map<String, dynamic>>('/api/feed');
    final body = response.data ?? const <String, dynamic>{};
    final items = requireList(body, 'items');
    return items
        .map((item) => Post.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}

/// Provides the [FeedRepository] bound to the configured [dioProvider].
///
/// Overridden with a fake in widget tests so the feed screen can render mock
/// data without a network.
final feedRepositoryProvider = Provider<FeedRepository>(
  (ref) => FeedRepository(ref.watch(dioProvider)),
);
