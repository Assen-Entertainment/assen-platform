import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:flutter/foundation.dart';

/// A catalog product — used across the store grid, the product detail screen,
/// and search results.
///
/// The app-side view model for the backend product resource, which has two
/// distinct shapes parsed by two factories:
///
/// * [Product.fromBrief] — the lean `ProductBrief` embedded in
///   `GET /api/search`, which carries only `id`/`type`/`title`/`price`/`meta`.
/// * [Product.fromDetail] — the full `ProductOut` envelope (`GET /api/products`,
///   `GET /api/products/{id}`), which additionally requires `media_url`,
///   `description`, `options`, `sold_out` and `locked`, and degrades the
///   server-optional creator descriptors, `stock` and `is_adult`.
///
/// Each factory parses *its own* required fields strictly, so a search brief
/// still constructs from five fields while a catalog row demands the full set.
/// When the generated `api_client` DTOs (P6) land they replace this parsing.
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

  /// Builds a [Product] from a search `ProductBrief` (the lean 5-field shape).
  ///
  /// The brief's required fields — `id`, `type`, `title`, `price`, `meta` — are
  /// parsed strictly: a missing key or the wrong type throws [ArgumentError] so
  /// a backend field-name drift surfaces as a load error. [id] is read through
  /// `toString()` so a string UUID or numeric PK both parse; [meta] degrades to
  /// null when the (required) string is empty. Every catalog/detail extra keeps
  /// its constructor default, since a brief does not carry them.
  factory Product.fromBrief(Map<String, dynamic> json) {
    return Product(
      id: _requireId(json),
      type: requireString(json, 'type'),
      title: requireString(json, 'title'),
      price: requireInt(json, 'price'),
      meta: nonEmpty(requireString(json, 'meta')),
    );
  }

  /// Builds a [Product] from a full catalog/detail `ProductOut` envelope.
  ///
  /// The `ProductOut`-required fields — `id`, `type`, `title`, `price`, `meta`,
  /// `media_url`, `description`, `options`, `sold_out`, `locked` — are parsed
  /// strictly: a missing key or the wrong type throws [ArgumentError] so a
  /// backend field-name drift surfaces as a load error rather than a silent
  /// blank. Only the server-optional fields degrade: `creator_id` to null,
  /// `creator_name`/`creator_handle` to an empty string, `is_adult` to false,
  /// and `stock` to null (unlimited/unknown) unless the server sends a number.
  /// [id] is read through `toString()`; [meta]/[mediaUrl] become null when the
  /// (required) string is empty. An empty `options` list is a valid value.
  factory Product.fromDetail(Map<String, dynamic> json) {
    final dynamic rawStock = json['stock'];
    return Product(
      id: _requireId(json),
      type: requireString(json, 'type'),
      title: requireString(json, 'title'),
      price: requireInt(json, 'price'),
      meta: nonEmpty(requireString(json, 'meta')),
      mediaUrl: nonEmpty(requireString(json, 'media_url')),
      description: requireString(json, 'description'),
      options: requireStringList(json, 'options'),
      soldOut: requireBool(json, 'sold_out'),
      locked: requireBool(json, 'locked'),
      creatorId: nonEmpty(json['creator_id']?.toString()),
      creatorName: json['creator_name'] as String? ?? '',
      creatorHandle: json['creator_handle'] as String? ?? '',
      stock: rawStock == null ? null : asInt(rawStock),
      isAdult: json['is_adult'] as bool? ?? false,
    );
  }

  /// Reads the contract-required `id`, coerced via `toString()`.
  ///
  /// A *missing* `id` is a contract violation and throws [ArgumentError]; a
  /// string UUID or a numeric PK both parse. Shared by [Product.fromBrief] and
  /// [Product.fromDetail].
  static String _requireId(Map<String, dynamic> json) {
    final dynamic rawId = json['id'];
    if (rawId == null) {
      throw ArgumentError.value(
        json,
        'json',
        'product payload is missing the required "id" field',
      );
    }
    return rawId.toString();
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
}
