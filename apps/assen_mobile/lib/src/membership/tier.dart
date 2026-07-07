import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:flutter/foundation.dart';

/// A membership tier offered by a creator.
///
/// The app-side view model for the backend `TierOut` shape
/// (`GET /api/tiers?creator_id=`, which returns a bare `list[TierOut]` — not a
/// paged envelope). The generated `api_client` DTOs (P6) don't exist yet, so
/// the membership section parses the contract JSON into this model; when the
/// generated layer lands it replaces this parsing.
@immutable
class Tier {
  /// Creates a tier view model.
  const Tier({
    required this.id,
    required this.name,
    required this.price,
    this.creatorId,
    this.period = '',
    this.benefits = const <String>[],
    this.badge = '',
    this.featured = false,
    this.sortOrder = 0,
  });

  /// Builds a [Tier] from a backend `TierOut` JSON object.
  ///
  /// The contract requires [id] and [name]; a payload missing either violates
  /// the server contract and throws, so a malformed row surfaces as a load
  /// error rather than a blank card. [id] is read through `toString()` so a
  /// string
  /// UUID or numeric PK both parse. [price]/[sortOrder] degrade to 0 and
  /// [period]/[badge] to an empty string when absent; [benefits] to an empty
  /// list and [featured] to false.
  factory Tier.fromJson(Map<String, dynamic> json) {
    final dynamic rawId = json['id'];
    final name = json['name'] as String?;
    if (rawId == null || name == null) {
      throw ArgumentError.value(
        json,
        'json',
        'tier payload is missing the required "id"/"name" fields',
      );
    }
    return Tier(
      id: rawId.toString(),
      creatorId: nonEmpty(json['creator_id']?.toString()),
      name: name,
      price: asInt(json['price']),
      period: json['period'] as String? ?? '',
      benefits: _stringList(json['benefits']),
      badge: json['badge'] as String? ?? '',
      featured: json['featured'] as bool? ?? false,
      sortOrder: asInt(json['sort_order']),
    );
  }

  /// Stable server identifier (a string UUID in the current contract).
  final String id;

  /// Optional owning-creator id (server `creator_id`); null when absent.
  final String? creatorId;

  /// The tier name (server `name`, e.g. "하츠코이").
  final String name;

  /// The price in KRW won (server `price`).
  final int price;

  /// The billing period label (server `period`, e.g. "월"); empty when unset.
  final String period;

  /// The tier benefits (server `benefits`); empty when none.
  final List<String> benefits;

  /// An optional badge label (server `badge`); empty when unset.
  final String badge;

  /// Whether the tier is highlighted as recommended (server `featured`).
  final bool featured;

  /// The display sort order (server `sort_order`).
  final int sortOrder;

  /// The price formatted as `₩12,000` with thousands separators.
  ///
  /// A local formatter (the app has no `intl` dependency) so a price always
  /// renders grouped rather than as a bare run of digits.
  String get priceLabel => '₩${formatThousands(price)}';

  /// The price + period line (e.g. `₩9,900 / 월`), or just the price when the
  /// period is unset.
  String get pricePeriodLabel =>
      period.isEmpty ? priceLabel : '$priceLabel / $period';

  /// Defensively coerces a JSON `benefits` value into a `List<String>`.
  ///
  /// The server sends `list[str]`, but a malformed row (a bare string or null)
  /// must not split into characters or throw — it degrades to an empty list.
  static List<String> _stringList(Object? value) => value is List
      ? value.map((e) => e.toString()).toList(growable: false)
      : const <String>[];
}
