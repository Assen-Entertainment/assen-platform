import 'package:flutter/foundation.dart';

/// The authenticated fan's identity summary shown on the 마이 tab.
///
/// The app-side view model for the backend `FanMeOut` shape
/// (`GET /api/fan/me`). [handle]/[avatarUrl] are populated only when the
/// account operates a creator profile; [nickname] is the sole display PII. The
/// [adultVerified]/[kycStatus] flags are derived 인증 state (never PII) used to
/// drive gating later. When the generated `api_client` DTOs (P6) land they
/// replace this parsing.
@immutable
class FanMe {
  /// Creates a fan identity summary.
  const FanMe({
    required this.id,
    required this.nickname,
    required this.role,
    this.handle,
    this.avatarUrl,
    this.adultVerified = false,
    this.kycStatus = 'unverified',
  });

  /// Builds a [FanMe] from a backend `FanMeOut` JSON object.
  ///
  /// The contract requires [id], [nickname] and [role]; a payload missing any
  /// of them violates the contract and throws. [handle]/[avatarUrl] become
  /// null when absent or empty (the account operates no creator); the derived
  /// flags fall back to their fail-closed defaults.
  factory FanMe.fromJson(Map<String, dynamic> json) {
    final dynamic rawId = json['id'];
    final nickname = json['nickname'] as String?;
    final role = json['role'] as String?;
    if (rawId == null || nickname == null || role == null) {
      throw ArgumentError.value(
        json,
        'json',
        'fan payload is missing a required "id"/"nickname"/"role" field',
      );
    }
    return FanMe(
      id: rawId.toString(),
      nickname: nickname,
      role: role,
      handle: _nonEmpty(json['handle'] as String?),
      avatarUrl: _nonEmpty(json['avatar_url'] as String?),
      adultVerified: json['adult_verified'] as bool? ?? false,
      kycStatus: json['kyc_status'] as String? ?? 'unverified',
    );
  }

  static String? _nonEmpty(String? value) =>
      (value != null && value.isNotEmpty) ? value : null;

  /// The account's stable fan id (server `id`).
  final String id;

  /// The fan's display nickname (server `nickname`).
  final String nickname;

  /// The account role (server `role`, e.g. `fan`/`creator`).
  final String role;

  /// The creator handle when the account operates one, else null.
  final String? handle;

  /// The creator avatar URL when the account operates one, else null.
  final String? avatarUrl;

  /// Whether the account passed 19+ 본인인증 (derived flag, not PII).
  final bool adultVerified;

  /// The KYC status string (server `kyc_status`); `unverified` by default.
  final String kycStatus;
}
