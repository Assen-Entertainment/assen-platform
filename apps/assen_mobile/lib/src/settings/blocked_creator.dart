import 'package:flutter/foundation.dart';

/// One creator the signed-in fan has personally blocked (`GET /api/fan/blocks`).
///
/// The app-side view model for the backend `BlockedCreatorOut` shape (ASS-226).
/// A personal block hides the creator from the fan's OWN aggregate surfaces
/// (feed/discovery/search) and auto-unfollows — it is fan-controlled, not
/// operator moderation, and carries no reason code.
@immutable
class BlockedCreator {
  /// Creates a blocked-creator entry.
  const BlockedCreator({
    required this.creatorId,
    required this.name,
    required this.handle,
  });

  /// Builds a [BlockedCreator] from a `BlockedCreatorOut` JSON object.
  ///
  /// The contract requires all three fields; a payload missing any of them
  /// violates the contract and throws rather than rendering a blank row.
  factory BlockedCreator.fromJson(Map<String, dynamic> json) {
    final dynamic creatorId = json['creator_id'];
    final name = json['name'] as String?;
    final handle = json['handle'] as String?;
    if (creatorId == null || name == null || handle == null) {
      throw ArgumentError(
        'blocked-creator payload is missing a required '
        '"creator_id"/"name"/"handle" field',
      );
    }
    return BlockedCreator(
      creatorId: creatorId.toString(),
      name: name,
      handle: handle,
    );
  }

  /// The blocked creator's stable id (server `creator_id`).
  final String creatorId;

  /// The blocked creator's display name (server `name`).
  final String name;

  /// The blocked creator's handle (server `handle`).
  final String handle;
}
