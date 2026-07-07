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
    required this.creatorId,
    required this.creatorName,
    required this.createdAt,
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
  /// The contract-required fields — `id`, `creator_id`, `creator_name`,
  /// `creator_handle`, `verified`, `body`, `media_url`, `like_count`,
  /// `comment_count` and a parseable `created_at` — are parsed strictly: a
  /// missing key or the wrong type throws [ArgumentError] so a backend
  /// field-name drift surfaces as a load error rather than a silent `₩0`/blank.
  /// Only `liked` and `is_adult` (server defaults) degrade to `false`. [id] is
  /// read through `toString()` so a string UUID or numeric PK both parse;
  /// [mediaUrl] degrades to null when the (required) `media_url` string is
  /// empty. An empty `body`/`media_url` is a valid value, not an error.
  factory Post.fromJson(Map<String, dynamic> json) {
    final dynamic rawId = json['id'];
    if (rawId == null) {
      throw ArgumentError.value(
        json,
        'json',
        'post payload is missing the required "id" field',
      );
    }
    final createdAt = DateTime.tryParse(requireString(json, 'created_at'));
    if (createdAt == null) {
      throw ArgumentError.value(
        json,
        'json',
        'post "created_at" is not a valid ISO-8601 datetime',
      );
    }
    return Post(
      id: rawId.toString(),
      creatorId: requireString(json, 'creator_id'),
      creatorName: requireString(json, 'creator_name'),
      creatorHandle: requireString(json, 'creator_handle'),
      verified: requireBool(json, 'verified'),
      body: requireString(json, 'body'),
      mediaUrl: nonEmpty(requireString(json, 'media_url')),
      likeCount: requireInt(json, 'like_count'),
      commentCount: requireInt(json, 'comment_count'),
      liked: json['liked'] as bool? ?? false,
      isAdult: json['is_adult'] as bool? ?? false,
      createdAt: createdAt,
    );
  }

  /// Stable server identifier (a string UUID in the current contract).
  final String id;

  /// The author-creator id (server `creator_id`, contract-required).
  final String creatorId;

  /// The author-creator display name (`creator_name`, contract-required).
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
