import 'package:flutter/foundation.dart';

/// A creator surfaced on the discovery (home) feed.
///
/// This is the app-side view model for the backend creator resource
/// (`GET /api/creators` → `CreatorOut`). The generated `api_client` DTOs
/// (P6, swagger_parser) don't exist yet, so the home screen parses the contract
/// JSON into this model; when the generated layer lands it replaces this
/// parsing (CONSTRAINTS #15/#32).
@immutable
class Creator {
  /// Creates a creator view model.
  const Creator({
    required this.id,
    required this.handle,
    required this.displayName,
    this.category,
    this.avatarUrl,
  });

  /// Builds a [Creator] from a backend `CreatorOut` JSON object.
  ///
  /// The contract requires [id] and [handle]; a payload missing either violates
  /// the server contract and throws, so a malformed row surfaces as a feed
  /// error rather than rendering blank. [id] is read defensively through
  /// `toString()` so either a string UUID (the current server shape) or a
  /// numeric PK is accepted. Only the optional descriptors degrade gracefully:
  /// [displayName] falls back to [handle] when `name` is absent/empty, and
  /// [category]/[avatarUrl] become null when the server sends an empty string.
  factory Creator.fromJson(Map<String, dynamic> json) {
    final dynamic rawId = json['id'];
    final handle = json['handle'] as String?;
    if (rawId == null || handle == null) {
      throw ArgumentError.value(
        json,
        'json',
        'creator payload is missing the required "id"/"handle" fields',
      );
    }
    final name = json['name'] as String?;
    return Creator(
      id: rawId.toString(),
      handle: handle,
      displayName: (name != null && name.isNotEmpty) ? name : handle,
      category: _nonEmpty(json['category'] as String?),
      avatarUrl: _nonEmpty(json['avatar_url'] as String?),
    );
  }

  /// Returns [value] when it is a non-empty string, otherwise null.
  ///
  /// The server sends `""` (not omission) for an unset descriptor; an empty
  /// avatar URL or category should read as absent — an initials fallback and no
  /// subtitle — rather than a broken image or a dangling separator.
  static String? _nonEmpty(String? value) =>
      (value != null && value.isNotEmpty) ? value : null;

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
}
