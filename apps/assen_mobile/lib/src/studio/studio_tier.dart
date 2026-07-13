import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:flutter/foundation.dart';

/// One of the signed-in creator's membership tiers, owner view.
///
/// The app-side view model for the backend `StudioTierOut` shape
/// (`GET /api/studio/tiers`). Adds the management fields the fan-facing tier view
/// omits — [active], [subscribers], [featured]. [subscribers] is a count of
/// active subscriptions (ASS-264), never a settlement/revenue figure. When the
/// generated `api_client` DTOs (P6) land they replace this parsing.
@immutable
class StudioTier {
  /// Creates a studio (owner-view) tier.
  const StudioTier({
    required this.id,
    required this.name,
    required this.price,
    required this.period,
    required this.benefits,
    required this.active,
    required this.subscribers,
    required this.featured,
    required this.isFree,
  });

  /// Builds a [StudioTier] from a `StudioTierOut` JSON object.
  ///
  /// The contract-required fields — `id`, `name`, `price`, `subscribers` — are
  /// parsed strictly; the rest degrade to their fail-closed defaults. `is_free`
  /// is derived from `pricing_kind` (ASS-297) so a price-0 paid tier is not
  /// mislabelled as free.
  factory StudioTier.fromJson(Map<String, dynamic> json) {
    final dynamic rawId = json['id'];
    if (rawId == null) {
      throw ArgumentError('studio tier payload is missing a required "id"');
    }
    final rawBenefits = json['benefits'];
    final benefits = rawBenefits is List
        ? rawBenefits.map((e) => e.toString()).toList()
        : const <String>[];
    return StudioTier(
      id: rawId.toString(),
      name: requireString(json, 'name'),
      price: requireInt(json, 'price'),
      period: json['period'] as String? ?? '월',
      benefits: benefits,
      active: json['active'] as bool? ?? true,
      subscribers: requireInt(json, 'subscribers'),
      featured: json['featured'] as bool? ?? false,
      isFree: (json['pricing_kind'] as String? ?? 'paid') == 'free',
    );
  }

  /// The tier's stable id (server `id`).
  final String id;

  /// The tier name (server `name`).
  final String name;

  /// The tier price in KRW won (server `price`); 0 for a free tier.
  final int price;

  /// The billing period label (server `period`, e.g. `월`).
  final String period;

  /// The tier benefits (server `benefits`).
  final List<String> benefits;

  /// Whether the tier is active/published (server `active`).
  final bool active;

  /// Active subscribers to this tier (server `subscribers`); a count only.
  final int subscribers;

  /// Whether the tier is featured (server `featured`).
  final bool featured;

  /// Whether this is a free tier (derived from server `pricing_kind`).
  final bool isFree;

  /// The price formatted as `무료` or `₩9,900 / 월`.
  String get priceLabel =>
      isFree ? '무료' : '₩${formatThousands(price)} / $period';
}
