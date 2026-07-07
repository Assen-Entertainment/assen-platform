import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:flutter/foundation.dart';

/// A catalog product — used across the store grid, the product detail screen,
/// and search results.
///
/// The app-side view model for the backend product resource: the `ProductOut`
/// envelope (`GET /api/products`, `GET /api/products/{id}`) and the leaner
/// `ProductBrief` embedded in `GET /api/search`. The brief only carries
/// [id]/[type]/[title]/[price]/[meta]; the fuller catalog/detail rows add the
/// creator descriptors, [mediaUrl], [description], [options] and the
/// [stock]/[soldOut]/[locked] browse flags. Every extra field degrades to a
/// safe default so a brief (search) row still constructs. When the generated
/// `api_client` DTOs (P6) land they replace this parsing.
@immutable
class Product {
  /// Creates a product view model.
  const Product({
    required this.id,
    required this.type,
    required this.title,
    required this.price,
    this.meta,
    this.creatorId,
    this.creatorName = '',
    this.creatorHandle = '',
    this.mediaUrl,
    this.description = '',
    this.options = const <String>[],
    this.stock,
    this.soldOut = false,
    this.locked = false,
    this.isAdult = false,
  });

  /// Builds a [Product] from a backend `ProductOut`/`ProductBrief` JSON object.
  ///
  /// The contract requires [id] and [title]; a payload missing either violates
  /// the server contract and throws. [id] is read through `toString()` so a
  /// string UUID or numeric PK both parse. [type] degrades to an empty string
  /// (no tag) and [price] to 0 when absent/wrong-typed; [meta]/[mediaUrl] become
  /// null when the server sends an empty string. The catalog/detail extras
  /// ([creator*], [description], [options], [stock], [soldOut], [locked],
  /// [isAdult]) fall back to their empty/false defaults so a leaner search brief
  /// still constructs. [stock] stays null (unlimited/unknown) unless the server
  /// sends a number.
  factory Product.fromJson(Map<String, dynamic> json) {
    final dynamic rawId = json['id'];
    final title = json['title'] as String?;
    if (rawId == null || title == null) {
      throw ArgumentError.value(
        json,
        'json',
        'product payload is missing the required "id"/"title" fields',
      );
    }
    final dynamic rawStock = json['stock'];
    return Product(
      id: rawId.toString(),
      type: json['type'] as String? ?? '',
      title: title,
      price: asInt(json['price']),
      meta: nonEmpty(json['meta'] as String?),
      creatorId: nonEmpty(json['creator_id']?.toString()),
      creatorName: json['creator_name'] as String? ?? '',
      creatorHandle: json['creator_handle'] as String? ?? '',
      mediaUrl: nonEmpty(json['media_url'] as String?),
      description: json['description'] as String? ?? '',
      options: _stringList(json['options']),
      stock: rawStock == null ? null : asInt(rawStock),
      soldOut: json['sold_out'] as bool? ?? false,
      locked: json['locked'] as bool? ?? false,
      isAdult: json['is_adult'] as bool? ?? false,
    );
  }

  /// Stable server identifier (a string UUID in the current contract).
  final String id;

  /// The product type (server `type`, e.g. `goods`/`ticket`); drives the tag.
  final String type;

  /// The product title.
  final String title;

  /// The price in KRW won (server `price`).
  final int price;

  /// Optional secondary line (server `meta`); null when unset.
  final String? meta;

  /// Optional owning-creator id (server `creator_id`); null for a global
  /// catalog item or a search brief.
  final String? creatorId;

  /// Owning-creator display name (server `creator_name`; empty for a global
  /// catalog item or a search brief).
  final String creatorName;

  /// Owning-creator @-handle (server `creator_handle`; empty for a global
  /// catalog item or a search brief).
  final String creatorHandle;

  /// Optional media image URL (server `media_url`); null when unset.
  final String? mediaUrl;

  /// Long-form description shown on the detail screen (server `description`).
  final String description;

  /// Purchase options (server `options`, e.g. sizes); empty when none.
  final List<String> options;

  /// Remaining stock (server `stock`); null means unlimited/unknown.
  final int? stock;

  /// Whether the item is sold out (server `sold_out`).
  final bool soldOut;

  /// Whether the item is members-only / locked (server `locked`).
  final bool locked;

  /// Whether the item is 19+ (server `is_adult`); the server already gates
  /// exposure, so this only drives a badge when a row surfaces.
  final bool isAdult;

  /// The Korean tag label for [type] (mirrors the web `MonetizableItem` map).
  ///
  /// Falls back to the raw [type] for an unknown value so a new server type
  /// still renders a label rather than nothing.
  String get typeLabel => switch (type) {
    'goods' => '굿즈',
    'digital' => '디지털',
    'experience' => '체험',
    'ticket' => '티켓',
    'coupon' => '쿠폰',
    'membership' => '멤버십',
    _ => type,
  };

  /// The price formatted as `₩12,000` with thousands separators.
  ///
  /// A local formatter (the app has no `intl` dependency) so a price always
  /// renders grouped rather than as a bare run of digits.
  String get priceLabel => '₩${formatThousands(price)}';

  /// Defensively coerces a JSON `options` value into a `List<String>`.
  ///
  /// The server sends `list[str]`, but a malformed row (a bare string or null)
  /// must not split into characters or throw — it degrades to an empty list.
  static List<String> _stringList(Object? value) => value is List
      ? value.map((e) => e.toString()).toList(growable: false)
      : const <String>[];
}
