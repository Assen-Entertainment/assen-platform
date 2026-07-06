import 'package:flutter/foundation.dart';

/// An in-app notification shown on the 알림 tab.
///
/// The app-side view model for the backend `NotificationOut` shape
/// (`GET /api/notifications` → `NotificationPage.items`). Named
/// [AppNotification] to avoid colliding with platform types; when the generated
/// `api_client` DTOs (P6) land they replace this parsing.
@immutable
class AppNotification {
  /// Creates a notification view model.
  const AppNotification({
    required this.id,
    required this.kind,
    required this.title,
    required this.createdAt,
    this.href = '',
    this.read = false,
  });

  /// Builds an [AppNotification] from a backend `NotificationOut` JSON object.
  ///
  /// The contract requires [id], [kind], [title] and a parseable `created_at`;
  /// a payload missing any of them violates the contract and throws, so a
  /// malformed row surfaces as a load error rather than an undated blank. [id]
  /// is read through `toString()` so a string UUID or a numeric PK both parse.
  /// [href]/[read] degrade to `''`/false when absent.
  factory AppNotification.fromJson(Map<String, dynamic> json) {
    final dynamic rawId = json['id'];
    final kind = json['kind'] as String?;
    final title = json['title'] as String?;
    final createdAt = DateTime.tryParse(json['created_at'] as String? ?? '');
    if (rawId == null || kind == null || title == null || createdAt == null) {
      throw ArgumentError.value(
        json,
        'json',
        'notification payload is missing a required '
            '"id"/"kind"/"title"/"created_at" field',
      );
    }
    return AppNotification(
      id: rawId.toString(),
      kind: kind,
      title: title,
      createdAt: createdAt,
      href: json['href'] as String? ?? '',
      read: json['read'] as bool? ?? false,
    );
  }

  /// Stable server identifier (a string UUID in the current contract).
  final String id;

  /// The notification kind (server `kind`), e.g. `order`/`comment`.
  final String kind;

  /// The human-readable notification title.
  final String title;

  /// When the notification was created (server `created_at`, ISO-8601).
  final DateTime createdAt;

  /// The in-app deep-link target (server `href`); empty when none.
  final String href;

  /// Whether the fan has read the notification (server `read`).
  final bool read;
}
