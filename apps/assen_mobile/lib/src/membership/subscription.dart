import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:flutter/foundation.dart';

/// A fan's membership subscription shown on the 내 구독 (subscriptions) screen.
///
/// The app-side view model for the backend `SubscriptionOut` shape
/// (`GET /api/subscriptions`). [nextBillingDate] is null for a free membership
/// (ASS-297) — no next charge — and [isFree] hides the billing UI. This is a
/// READ surface: subscribe/cancel/change-tier are payment gates and are
/// deliberately not wired here. When the generated `api_client` DTOs (P6) land
/// they replace this parsing.
@immutable
class Subscription {
  /// Creates a subscription view model.
  const Subscription({
    required this.id,
    required this.creatorName,
    required this.creatorHandle,
    required this.tierName,
    required this.price,
    required this.period,
    required this.status,
    required this.cancelScheduled,
    required this.isFree,
    this.creatorId,
    this.tierId,
    this.nextBillingDate,
  });

  /// Builds a [Subscription] from a backend `SubscriptionOut` JSON object.
  ///
  /// The contract-required fields — `id`, `price`, `status` — are parsed
  /// strictly; the creator/tier display fields degrade to empty and the flags to
  /// their fail-closed defaults so a partial payload renders a safe row rather
  /// than throwing on display-only text. `creator_id`/`tier_id` degrade to null
  /// (a since-deleted creator/tier); `next_billing_date` parses to null for a
  /// free membership.
  factory Subscription.fromJson(Map<String, dynamic> json) {
    final dynamic rawId = json['id'];
    if (rawId == null) {
      throw ArgumentError('subscription payload is missing a required "id"');
    }
    return Subscription(
      id: rawId.toString(),
      creatorId: nonEmpty(json['creator_id']?.toString()),
      creatorName: json['creator_name'] as String? ?? '',
      creatorHandle: json['creator_handle'] as String? ?? '',
      tierId: nonEmpty(json['tier_id']?.toString()),
      tierName: json['tier_name'] as String? ?? '',
      price: requireInt(json, 'price'),
      period: json['period'] as String? ?? '',
      status: requireString(json, 'status'),
      nextBillingDate: DateTime.tryParse(
        json['next_billing_date'] as String? ?? '',
      ),
      cancelScheduled: json['cancel_scheduled'] as bool? ?? false,
      isFree: json['is_free'] as bool? ?? false,
    );
  }

  /// The subscription's stable id (server `id`).
  final String id;

  /// The owning creator's id (server `creator_id`); null when since-deleted.
  final String? creatorId;

  /// The owning creator's display name (server `creator_name`).
  final String creatorName;

  /// The owning creator's handle (server `creator_handle`).
  final String creatorHandle;

  /// The subscribed tier's id (server `tier_id`); null when since-deleted.
  final String? tierId;

  /// The subscribed tier's name (server `tier_name`).
  final String tierName;

  /// The tier price in KRW won (server `price`); 0 for a free membership.
  final int price;

  /// The billing period (server `period`, e.g. `monthly`).
  final String period;

  /// The subscription lifecycle state (server `status`, e.g. `active`).
  final String status;

  /// The next charge date (server `next_billing_date`); null when free.
  final DateTime? nextBillingDate;

  /// Whether the fan has set this active subscription to end at period-end.
  final bool cancelScheduled;

  /// Whether this is a free membership (server `is_free`); hides billing UI.
  final bool isFree;

  /// The Korean label for [status], accounting for the 해지 예정 state.
  String get statusLabel {
    if (cancelScheduled && status == 'active') return '해지 예정';
    return switch (status) {
      'active' => '이용중',
      'expired' => '만료',
      'cancelled' => '해지',
      _ => status,
    };
  }

  /// The price formatted as `무료` or `₩12,000`.
  String get priceLabel => isFree ? '무료' : '₩${formatThousands(price)}';
}
