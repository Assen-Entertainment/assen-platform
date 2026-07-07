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
    required this.author,
    required this.body,
    required this.createdAt,
    this.postId,
  });

  /// Builds a [Comment] from a backend `CommentOut` JSON object.
  ///
  /// The contract requires [id] and a parseable `created_at`; a payload missing
  /// either violates the contract and throws, so a malformed row surfaces as a
  /// load error rather than an undated blank. [id] is read through `toString()`
  /// so a string UUID or numeric PK both parse. [author] falls back to `익명`
  /// (matching the server default) and [body] to an empty string when absent.
  factory Comment.fromJson(Map<String, dynamic> json) {
    final dynamic rawId = json['id'];
    final createdAt = DateTime.tryParse(json['created_at'] as String? ?? '');
    if (rawId == null || createdAt == null) {
      throw ArgumentError.value(
        json,
        'json',
        'comment payload is missing the required "id"/"created_at" fields',
      );
    }
    final author = json['author'] as String?;
    return Comment(
      id: rawId.toString(),
      postId: json['post_id']?.toString(),
      author: (author != null && author.isNotEmpty) ? author : '익명',
      body: json['body'] as String? ?? '',
      createdAt: createdAt,
    );
  }

  /// Stable server identifier (a string UUID in the current contract).
  final String id;

  /// Optional parent post id (server `post_id`); null when absent.
  final String? postId;

  /// The comment author's display name (server `author`; `익명` when absent).
  final String author;

  /// The comment body text (server `body`).
  final String body;

  /// When the comment was created (server `created_at`, ISO-8601).
  final DateTime createdAt;
}
