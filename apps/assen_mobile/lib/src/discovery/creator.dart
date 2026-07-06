import 'package:flutter/foundation.dart';

/// A creator surfaced on the discovery (home) feed.
///
/// This is the app-side view model for the backend creator resource. The
/// generated `api_client` DTOs (P6, swagger_parser) don't exist yet, so the
/// home screen parses the contract JSON into this model; when the generated
/// layer lands it replaces this parsing (CONSTRAINTS #15/#32).
@immutable
class Creator {
  /// Creates a creator view model.
  const Creator({
    required this.id,
    required this.handle,
    required this.displayName,
    this.tagline,
    this.avatarUrl,
    this.isLive = false,
  });

  /// Builds a [Creator] from the backend JSON object.
  ///
  /// Falls back to [handle] for the display name and to `false` for liveness so
  /// a partial payload never throws — the feed degrades gracefully instead.
  factory Creator.fromJson(Map<String, dynamic> json) {
    return Creator(
      id: json['id'] as String,
      handle: json['handle'] as String,
      displayName:
          (json['display_name'] as String?) ?? json['handle'] as String,
      tagline: json['tagline'] as String?,
      avatarUrl: json['avatar_url'] as String?,
      isLive: (json['is_live'] as bool?) ?? false,
    );
  }

  /// Stable server identifier.
  final String id;

  /// The @-handle used in the deep-linkable profile route.
  final String handle;

  /// The creator's display name.
  final String displayName;

  /// Optional short tagline shown under the name.
  final String? tagline;

  /// Optional avatar image URL (null shows an initials fallback).
  final String? avatarUrl;

  /// Whether the creator is currently live/on-air.
  final bool isLive;
}
