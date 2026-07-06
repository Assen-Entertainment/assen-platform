import 'package:flutter/foundation.dart';

/// A product surfaced in search results.
///
/// The app-side view model for the backend `ProductBrief` shape
/// (`GET /api/search` → `SearchOut.products`). Mirrors the web
/// `MonetizableItem` fields (type/title/price/meta); when the generated
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
  });

  /// Builds a [Product] from a backend `ProductBrief` JSON object.
  ///
  /// The contract requires [id] and [title]; a payload missing either violates
  /// the server contract and throws. [id] is read through `toString()` so a
  /// string UUID or a numeric PK both parse. [type] degrades to an empty string
  /// (no tag) and [price] to 0 when absent/wrong-typed; [meta] becomes null
  /// when the server sends an empty string.
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
    return Product(
      id: rawId.toString(),
      type: json['type'] as String? ?? '',
      title: title,
      price: _asInt(json['price']),
      meta: _nonEmpty(json['meta'] as String?),
    );
  }

  static String? _nonEmpty(String? value) =>
      (value != null && value.isNotEmpty) ? value : null;

  static int _asInt(Object? value) => switch (value) {
    final int v => v,
    final num v => v.toInt(),
    _ => 0,
  };

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
  String get priceLabel => '₩${_grouped(price)}';

  static String _grouped(int value) {
    final digits = value.abs().toString();
    final buffer = StringBuffer(value < 0 ? '-' : '');
    for (var i = 0; i < digits.length; i++) {
      if (i > 0 && (digits.length - i) % 3 == 0) buffer.write(',');
      buffer.write(digits[i]);
    }
    return buffer.toString();
  }
}
