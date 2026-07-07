import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:flutter/foundation.dart';

/// A feed post — shown on the global feed and on the post detail screen.
///
/// The app-side view model for the backend `PostOut` shape (`GET /api/feed`,
/// `GET /api/posts/{id}`). The generated `api_client` DTOs (P6) don't exist yet,
/// so the screens parse the contract JSON into this model; when the generated
/// layer lands it replaces this parsing.
@immutable
class Post {
  /// Creates a post view model.
  const Post({
    required this.id,
    required this.creatorName,
    required this.createdAt,
    this.creatorId,
    this.creatorHandle = '',
    this.verified = false,
    this.body = '',
    this.mediaUrl,
    this.likeCount = 0,
    this.commentCount = 0,
    this.liked = false,
    this.isAdult = false,
  });

  /// Builds a [Post] from a backend `PostOut` JSON object.
  ///
  /// The contract requires [id] and a parseable `created_at`; a payload missing
  /// either violates the contract and throws, so a malformed row surfaces as a
  /// load error rather than an undated blank. [id] is read through `toString()`
  /// so a string UUID or numeric PK both parse. [creatorName] falls back to the
  /// handle when `creator_name` is absent/empty; [body] degrades to an empty
  /// string, [mediaUrl] to null on an empty string, and the counts/flags to
  /// 0/false when absent or the wrong type.
  factory Post.fromJson(Map<String, dynamic> json) {
    final dynamic rawId = json['id'];
    final createdAt = DateTime.tryParse(json['created_at'] as String? ?? '');
    if (rawId == null || createdAt == null) {
      throw ArgumentError.value(
        json,
        'json',
        'post payload is missing the required "id"/"created_at" fields',
      );
    }
    final name = json['creator_name'] as String?;
    final handle = json['creator_handle'] as String? ?? '';
    return Post(
      id: rawId.toString(),
      creatorId: nonEmpty(json['creator_id']?.toString()),
      creatorName: (name != null && name.isNotEmpty) ? name : handle,
      creatorHandle: handle,
      verified: json['verified'] as bool? ?? false,
      body: json['body'] as String? ?? '',
      mediaUrl: nonEmpty(json['media_url'] as String?),
      likeCount: asInt(json['like_count']),
      commentCount: asInt(json['comment_count']),
      liked: json['liked'] as bool? ?? false,
      isAdult: json['is_adult'] as bool? ?? false,
      createdAt: createdAt,
    );
  }

  /// Stable server identifier (a string UUID in the current contract).
  final String id;

  /// Optional author-creator id (server `creator_id`); null when absent.
  final String? creatorId;

  /// The author-creator display name (server `creator_name`; falls back to the
  /// handle).
  final String creatorName;

  /// The author-creator @-handle (server `creator_handle`).
  final String creatorHandle;

  /// Whether the author-creator is verified (server `verified`).
  final bool verified;

  /// The post body text (server `body`); empty when none.
  final String body;

  /// Optional media image URL (server `media_url`); null when unset.
  final String? mediaUrl;

  /// The like count (server `like_count`).
  final int likeCount;

  /// The comment count (server `comment_count`).
  final int commentCount;

  /// Whether the authenticated caller has liked the post (server `liked`;
  /// always false for anonymous reads).
  final bool liked;

  /// Whether the post is 19+ (server `is_adult`); the server already gates
  /// exposure, so this only drives a badge when a row surfaces.
  final bool isAdult;

  /// When the post was created (server `created_at`, ISO-8601).
  final DateTime createdAt;

  /// The `@handle` identity line, or empty when the handle is unknown.
  String get handleLabel => creatorHandle.isEmpty ? '' : '@$creatorHandle';
}
