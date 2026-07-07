import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:flutter/foundation.dart';

/// A comment on a post, shown read-only on the post detail screen.
///
/// The app-side view model for the backend `CommentOut` shape
/// (`GET /api/posts/{id}/comments`). The server already resolves [author] to a
/// display name (never the internal fan id) and defaults it to `익명`; when the
/// generated `api_client` DTOs (P6) land they replace this parsing.
@immutable
class Comment {
  /// Creates a comment view model.
  const Comment({
    required this.id,
    required this.postId,
    required this.author,
    required this.body,
    required this.createdAt,
  });

  /// Builds a [Comment] from a backend `CommentOut` JSON object.
  ///
  /// The contract-required fields — `id`, `post_id`, `author`, `body` and a
  /// parseable `created_at` — are parsed strictly: a missing key or the wrong
  /// type throws [ArgumentError] so a backend field-name drift surfaces as a
  /// load error rather than an undated blank. [id] is read through `toString()`
  /// so a string UUID or numeric PK both parse. An empty `author` displays as
  /// `익명` (matching the server default); an empty `body` is a valid value.
  factory Comment.fromJson(Map<String, dynamic> json) {
    final dynamic rawId = json['id'];
    if (rawId == null) {
      throw ArgumentError.value(
        json,
        'json',
        'comment payload is missing the required "id" field',
      );
    }
    final createdAt = DateTime.tryParse(requireString(json, 'created_at'));
    if (createdAt == null) {
      throw ArgumentError.value(
        json,
        'json',
        'comment "created_at" is not a valid ISO-8601 datetime',
      );
    }
    final author = requireString(json, 'author');
    return Comment(
      id: rawId.toString(),
      postId: requireString(json, 'post_id'),
      author: author.isEmpty ? '익명' : author,
      body: requireString(json, 'body'),
      createdAt: createdAt,
    );
  }

  /// Stable server identifier (a string UUID in the current contract).
  final String id;

  /// The parent post id (server `post_id`, contract-required).
  final String postId;

  /// The comment author's display name (server `author`; `익명` when empty).
  final String author;

  /// The comment body text (server `body`).
  final String body;

  /// When the comment was created (server `created_at`, ISO-8601).
  final DateTime createdAt;
}
