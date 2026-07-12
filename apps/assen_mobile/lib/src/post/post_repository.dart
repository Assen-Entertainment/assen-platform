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

/// The like state a like/unlike toggle resolves to: the server's fresh truth.
///
/// A tiny record (not a model) carrying just the two fields
/// `PUT|DELETE /api/posts/{id}/like` answers with (`{liked, like_count}`), so
/// the controller can reconcile its optimistic flip against the authoritative
/// count.
typedef LikeState = ({bool liked, int likeCount});

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

  /// Likes or unlikes a post via `PUT`/`DELETE /api/posts/{id}/like`.
  ///
  /// [liked] true sends the PUT (like), false the DELETE (unlike); both are
  /// idempotent server-side and answer `{liked, like_count}`, returned here as
  /// the authoritative [LikeState] the controller reconciles against. A 404
  /// (an unknown or 19+-gated post) is translated into a
  /// [PostNotFoundException]; other transport errors (e.g. a 422 personal-block
  /// refusal) propagate for the caller to surface.
  Future<LikeState> setLike(String postId, {required bool liked}) async {
    final path = '/api/posts/${Uri.encodeComponent(postId)}/like';
    try {
      final response = liked
          ? await _dio.put<Map<String, dynamic>>(path)
          : await _dio.delete<Map<String, dynamic>>(path);
      final body = response.data ?? const <String, dynamic>{};
      return (
        liked: requireBool(body, 'liked'),
        likeCount: requireInt(body, 'like_count'),
      );
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        throw PostNotFoundException(postId);
      }
      rethrow;
    }
  }

  /// Adds a comment to a post via `POST /api/posts/{id}/comments`.
  ///
  /// Sends `{body}` and maps the returned `CommentOut` (HTTP 201) into a
  /// [Comment] the controller appends to the thread. A 404 (an unknown or
  /// gated post) is translated into a [PostNotFoundException]; other transport
  /// errors (e.g. a 422 personal-block refusal) propagate for the caller to
  /// surface.
  Future<Comment> addComment(String postId, String body) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/posts/${Uri.encodeComponent(postId)}/comments',
        data: <String, dynamic>{'body': body},
      );
      return Comment.fromJson(response.data ?? const <String, dynamic>{});
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
