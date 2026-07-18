import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:flutter/foundation.dart';

/// One follower of a creator, shown on the 팔로워 (followers) list.
///
/// The app-side view model for the backend `FollowerOut` shape
/// (`GET /api/creators/{handle}/followers`). Carries only already-public
/// display identity — [nickname], and (when the follower is a creator) their
/// [handle]/[avatarUrl] so the row links to that profile. No contact/identity
/// PII. When the generated `api_client` DTOs (P6) land they replace this.
@immutable
class Follower {
  /// Creates a follower entry.
  const Follower({
    required this.id,
    required this.nickname,
    required this.isCreator,
    this.handle = '',
    this.avatarUrl,
  });

  /// Builds a [Follower] from a backend `FollowerOut` JSON object.
  ///
  /// The contract-required [id] is parsed strictly; the display fields degrade
  /// to their fail-closed defaults so a partial payload renders a safe row.
  /// [avatarUrl] becomes null when the (server-optional) string is empty.
  factory Follower.fromJson(Map<String, dynamic> json) {
    final dynamic rawId = json['id'];
    if (rawId == null) {
      throw ArgumentError('follower payload is missing a required "id"');
    }
    return Follower(
      id: rawId.toString(),
      nickname: json['nickname'] as String? ?? '',
      isCreator: json['is_creator'] as bool? ?? false,
      handle: json['handle'] as String? ?? '',
      avatarUrl: nonEmpty(json['avatar_url'] as String?),
    );
  }

  /// The follow-edge id (server `id`); a stable list key.
  final String id;

  /// The follower's display nickname (server `nickname`).
  final String nickname;

  /// Whether the follower themselves operates a creator (server `is_creator`).
  final bool isCreator;

  /// The follower's own creator handle when [isCreator] (server `handle`).
  final String handle;

  /// The follower's own creator avatar when [isCreator] (server `avatar_url`).
  final String? avatarUrl;

  /// The `@handle` line for a creator follower, or empty for a plain fan.
  String get handleLabel => isCreator && handle.isNotEmpty ? '@$handle' : '';
}
