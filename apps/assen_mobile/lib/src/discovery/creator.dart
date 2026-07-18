import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:flutter/foundation.dart';

/// A creator surfaced on the discovery feed, in search, and on the profile
/// screen.
///
/// This is the app-side view model for the backend creator resource
/// (`GET /api/creators`, `GET /api/creators/{handle}`, `GET /api/search` →
/// `CreatorOut`). The generated `api_client` DTOs (P6, swagger_parser) don't
/// exist yet, so the screens parse the contract JSON into this model; when the
/// generated layer lands it replaces this parsing (CONSTRAINTS #15/#32).
///
/// The discovery feed only reads [handle]/[displayName]/[category]/[avatarUrl];
/// the R8 profile screen reads the fuller descriptor set ([bio]/[coverUrl]/
/// [accentColor]/[verified]) and the [followers]/[posts] stats. All of the
/// profile fields carry safe defaults so a partial row (e.g. a search hit)
/// still constructs.
@immutable
class Creator {
  /// Creates a creator view model.
  const Creator({
    required this.id,
    required this.handle,
    required this.displayName,
    this.category,
    this.avatarUrl,
    this.bio,
    this.coverUrl,
    this.accentColor,
    this.verified = false,
    this.followers = 0,
    this.posts = 0,
    this.following = false,
    this.blocked = false,
  });

  /// Builds a [Creator] from a backend `CreatorOut` JSON object.
  ///
  /// The contract requires [id] and [handle]; a payload missing either violates
  /// the server contract and throws, so a malformed row surfaces as a load
  /// error rather than rendering blank. [id] is read defensively through
  /// `toString()` so either a string UUID (the current server shape) or a
  /// numeric PK is accepted. The optional descriptors degrade gracefully:
  /// [displayName] falls back to [handle] when `name` is absent/empty, and
  /// [category]/[avatarUrl]/[bio]/[coverUrl]/[accentColor] become null when the
  /// server sends an empty string. [verified]/[following]/[blocked] default to
  /// false when absent, and [followers]/[posts] to 0 when absent or the wrong
  /// type.
  factory Creator.fromJson(Map<String, dynamic> json) {
    final dynamic rawId = json['id'];
    final handle = json['handle'] as String?;
    if (rawId == null || handle == null) {
      throw ArgumentError(
        'creator payload is missing the required "id"/"handle" fields',
      );
    }
    final name = json['name'] as String?;
    return Creator(
      id: rawId.toString(),
      handle: handle,
      displayName: (name != null && name.isNotEmpty) ? name : handle,
      category: nonEmpty(json['category'] as String?),
      avatarUrl: nonEmpty(json['avatar_url'] as String?),
      bio: nonEmpty(json['bio'] as String?),
      coverUrl: nonEmpty(json['cover_url'] as String?),
      accentColor: nonEmpty(json['accent_color'] as String?),
      verified: json['verified'] as bool? ?? false,
      followers: asInt(json['followers']),
      posts: asInt(json['posts']),
      following: json['following'] as bool? ?? false,
      blocked: json['blocked'] as bool? ?? false,
    );
  }

  /// Stable server identifier (a string UUID in the current contract).
  final String id;

  /// The @-handle used in the deep-linkable profile route.
  final String handle;

  /// The creator's display name (server `name`; falls back to [handle]).
  final String displayName;

  /// Optional category label shown under the name (server `category`).
  final String? category;

  /// Optional avatar image URL (null shows an initials fallback).
  final String? avatarUrl;

  /// Optional profile bio/description (server `bio`).
  final String? bio;

  /// Optional cover/banner image URL for the header (server `cover_url`).
  final String? coverUrl;

  /// Optional signature accent colour as a hex string (server `accent_color`).
  ///
  /// The profile screen parses this into an accessible accent via ui_kit's
  /// `CreatorAccent`; null (or an unparseable value) falls back to the brand
  /// rose.
  final String? accentColor;

  /// Whether the creator is verified (server `verified`).
  final bool verified;

  /// Follower count shown in the profile stats (server `followers`).
  final int followers;

  /// Post count shown in the profile stats (server `posts`).
  final int posts;

  /// Whether the authenticated caller follows this creator (server `following`;
  /// always false for anonymous reads).
  final bool following;

  /// Whether the authenticated caller has personally blocked this creator
  /// (server `blocked`; always false for anonymous reads).
  ///
  /// Discovery and search already exclude blocked creators, so this is only
  /// meaningful on an explicit profile navigation (`GET /api/creators/{handle}`
  /// returns the row instead of a 404); the profile screen renders a blocked
  /// state rather than the creator's content when it is true.
  final bool blocked;

  /// Returns a copy with the follow-affected fields overridden.
  ///
  /// Only [following] and [followers] — the fields a follow toggle mutates —
  /// are parameterised, so the profile controller can apply an optimistic
  /// follow (and reconcile it with the server's fresh follower count) without
  /// rebuilding the whole profile.
  Creator copyWith({bool? following, int? followers}) {
    return Creator(
      id: id,
      handle: handle,
      displayName: displayName,
      category: category,
      avatarUrl: avatarUrl,
      bio: bio,
      coverUrl: coverUrl,
      accentColor: accentColor,
      verified: verified,
      followers: followers ?? this.followers,
      posts: posts,
      following: following ?? this.following,
      blocked: blocked,
    );
  }
}
