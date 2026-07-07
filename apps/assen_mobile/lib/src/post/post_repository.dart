import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:assen_mobile/src/post/comment.dart';
import 'package:assen_mobile/src/post/post.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Thrown when `GET /api/posts/{id}` returns 404 (unknown/gated).
///
/// A typed marker (not a generic error) so the post detail screen can render
/// the dedicated "없는 게시물" state instead of the generic retry error. The server
/// 404s a 19+ gated post to a non-permitted viewer just like an unknown id (no
/// existence leak), so this covers both.
class PostNotFoundException implements Exception {
  /// Creates the not-found marker for [postId].
  const PostNotFoundException(this.postId);

  /// The post id that did not resolve.
  final String postId;

  @override
  String toString() => 'PostNotFoundException($postId)';
}

/// Fetches a single post and its comments from the backend.
///
/// A thin repository over [Dio] owning the endpoint paths and the JSON→model
/// mapping so the controller/UI stay transport-agnostic. When the generated
/// `api_client` (P6) lands, this delegates to it instead of calling Dio.
class PostRepository {
  /// Creates a repository backed by [_dio].
  const PostRepository(this._dio);

  final Dio _dio;

  /// Loads a single post via `GET /api/posts/{id}`.
  ///
  /// A 404 is translated into a [PostNotFoundException] so the screen shows the
  /// "unknown post" state; other transport errors propagate to the generic
  /// error
  /// state.
  Future<Post> fetchPost(String postId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/posts/${Uri.encodeComponent(postId)}',
      );
      return Post.fromJson(response.data ?? const <String, dynamic>{});
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        throw PostNotFoundException(postId);
      }
      rethrow;
    }
  }

  /// Loads a post's comments via `GET /api/posts/{id}/comments`.
  ///
  /// Maps the `CommentPage` envelope (`{items, next_cursor}`) into a list of
  /// [Comment]s, oldest first; only the first page is read here (cursor
  /// paging is
  /// a follow-up). The envelope is parsed strictly: the `items` array must be
  /// present (an empty array is the no-comments state), but a *missing* key
  /// is a
  /// contract violation and throws (an [ArgumentError] via [requireList]).
  /// A 404
  /// (the post is unknown or gated) is translated into a
  /// [PostNotFoundException].
  Future<List<Comment>> fetchComments(String postId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/posts/${Uri.encodeComponent(postId)}/comments',
      );
      final body = response.data ?? const <String, dynamic>{};
      final items = requireList(body, 'items');
      return items
          .map((item) => Comment.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        throw PostNotFoundException(postId);
      }
      rethrow;
    }
  }
}

/// Provides the [PostRepository] bound to the configured [dioProvider].
///
/// Overridden with a fake in widget tests so the post detail screen can render
/// mock data without a network.
final postRepositoryProvider = Provider<PostRepository>(
  (ref) => PostRepository(ref.watch(dioProvider)),
);
