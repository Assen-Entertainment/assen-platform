import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:flutter/foundation.dart';

/// One line of a fan's order (a purchase snapshot at checkout time).
///
/// The app-side view model for the backend `OrderItemOut` shape (embedded in
/// `OrderOut.items`). [title]/[type]/[option]/[price]/[qty] are contract-
/// required; [productId] degrades to null (the source product may be deleted).
/// When the generated `api_client` DTOs (P6) land they replace this parsing.
@immutable
class OrderItem {
  /// Creates an order line.
  const OrderItem({
    required this.title,
    required this.type,
    required this.option,
    required this.price,
    required this.qty,
    this.productId,
  });

  /// Builds an [OrderItem] from a backend `OrderItemOut` JSON object.
  ///
  /// The contract-required fields — `title`, `type`, `option`, `price`, `qty` —
  /// are parsed strictly (a missing key or wrong type throws [ArgumentError] so
  /// a backend field drift surfaces as a load error). Only `product_id` is
  /// server-optional and degrades to null (a since-deleted product line).
  factory OrderItem.fromJson(Map<String, dynamic> json) {
    return OrderItem(
      title: requireString(json, 'title'),
      type: requireString(json, 'type'),
      option: requireString(json, 'option'),
      price: requireInt(json, 'price'),
      qty: requireInt(json, 'qty'),
      productId: nonEmpty(json['product_id']?.toString()),
    );
  }

  /// The purchased product's snapshot title (server `title`).
  final String title;

  /// The product type (server `type`, e.g. `goods`/`ticket`).
  final String type;

  /// The chosen purchase option (server `option`); empty when none.
  final String option;

  /// The unit price in KRW won at purchase (server `price`).
  final int price;

  /// The purchased quantity (server `qty`).
  final int qty;

  /// The source product id (server `product_id`); null when since-deleted.
  final String? productId;
}

/// The order's latest refund request, embedded on an [Order] when one exists.
///
/// The app-side view model for the backend `OrderRefundOut` shape. Both fields
/// are contract-required. When the generated `api_client` DTOs (P6) land they
/// replace this parsing.
@immutable
class OrderRefund {
  /// Creates a refund summary.
  const OrderRefund({required this.status, required this.reason});

  /// Builds an [OrderRefund] from a backend `OrderRefundOut` JSON object.
  ///
  /// Both `status` and `reason` are contract-required and parsed strictly (a
  /// missing key or wrong type throws [ArgumentError]).
  factory OrderRefund.fromJson(Map<String, dynamic> json) {
    return OrderRefund(
      status: requireString(json, 'status'),
      reason: requireString(json, 'reason'),
    );
  }

  /// The refund review state (server `status`, e.g. `requested`/`accepted`).
  final String status;

  /// The fan-supplied refund reason (server `reason`).
  final String reason;

  /// The Korean label for [status] (mirrors the web refund status map).
  ///
  /// Falls back to the raw [status] for an unknown value so a new server state
  /// still renders a label rather than nothing.
  String get refundLabel => switch (status) {
    'requested' => '환불 접수',
    'reviewing' => '환불 검토중',
    'accepted' => '환불 완료',
    'rejected' => '환불 거절',
    _ => status,
  };
}

/// A delivery-address snapshot echoed on a goods order (own orders only).
///
/// The app-side view model for the backend `OrderShippingOut` shape. All fields
/// are contract-required. This is only ever the signed-in fan's OWN order, but
/// [recipientPhone]/[postalCode] are still PII: they are held in memory for a
/// future order-detail surface only and MUST NOT be persisted locally or logged
/// (저장 PII 0 gate). The orders list deliberately never renders them.
@immutable
class OrderShipping {
  /// Creates a delivery-address snapshot.
  const OrderShipping({
    required this.recipientName,
    required this.recipientPhone,
    required this.postalCode,
    required this.address1,
    required this.address2,
  });

  /// Builds an [OrderShipping] from a backend `OrderShippingOut` JSON object.
  ///
  /// Every field is contract-required and parsed strictly (a missing key or
  /// wrong type throws [ArgumentError]).
  factory OrderShipping.fromJson(Map<String, dynamic> json) {
    return OrderShipping(
      recipientName: requireString(json, 'recipient_name'),
      recipientPhone: requireString(json, 'recipient_phone'),
      postalCode: requireString(json, 'postal_code'),
      address1: requireString(json, 'address1'),
      address2: requireString(json, 'address2'),
    );
  }

  /// The recipient's name (server `recipient_name`).
  final String recipientName;

  /// The recipient's phone (server `recipient_phone`); PII — display-only.
  final String recipientPhone;

  /// The delivery postal code (server `postal_code`); PII — display-only.
  final String postalCode;

  /// The first address line (server `address1`).
  final String address1;

  /// The detail address line (server `address2`); empty when none.
  final String address2;
}

/// A fan's order shown on the 주문 내역 (orders) screen.
///
/// The app-side view model for the backend `OrderOut` shape
/// (`GET /api/orders` → `OrderPage.items`). This is a READ-ONLY surface: order
/// placement, cancellation and refund requests are payment/legal gates and are
/// deliberately not wired here. When the generated `api_client` DTOs (P6) land
/// they replace this parsing.
@immutable
class Order {
  /// Creates an order view model.
  const Order({
    required this.id,
    required this.status,
    required this.createdAt,
    required this.items,
    required this.subtotal,
    required this.shippingFee,
    required this.total,
    this.shippingAddress,
    this.creatorName,
    this.refund,
  });

  /// Builds an [Order] from a backend `OrderOut` JSON object.
  ///
  /// The contract-required fields — `id`, `status`, a parseable `created_at`,
  /// `items`, `subtotal`, `shipping`, `shipping_fee`, `total` — are parsed
  /// strictly: a missing key or wrong type throws [ArgumentError] so a backend
  /// field drift surfaces as a load error rather than a silent blank. [id] is
  /// read through `toString()` so a string code or numeric PK both parse. The
  /// server-optional `shipping_address`/`creator_name`/`refund` degrade to null
  /// when absent. The error message embeds only the failing key name (never the
  /// payload) so a parse failure cannot leak the nested shipping PII.
  factory Order.fromJson(Map<String, dynamic> json) {
    final dynamic rawId = json['id'];
    final createdAt = DateTime.tryParse(json['created_at'] as String? ?? '');
    if (rawId == null || createdAt == null) {
      throw ArgumentError(
        'order payload is missing a required "id"/"created_at" field',
      );
    }
    // The server sends `shipping` and `shipping_fee` as duplicate required
    // fields (same value); validate `shipping`'s presence/type as a drift guard
    // even though only `shipping_fee` is stored (server: OrderOut.shipping).
    requireInt(json, 'shipping');
    final dynamic rawShipping = json['shipping_address'];
    final dynamic rawRefund = json['refund'];
    return Order(
      id: rawId.toString(),
      status: requireString(json, 'status'),
      createdAt: createdAt,
      items: requireList(json, 'items')
          .map((item) => OrderItem.fromJson(item as Map<String, dynamic>))
          .toList(growable: false),
      subtotal: requireInt(json, 'subtotal'),
      shippingFee: requireInt(json, 'shipping_fee'),
      total: requireInt(json, 'total'),
      shippingAddress: rawShipping is Map<String, dynamic>
          ? OrderShipping.fromJson(rawShipping)
          : null,
      creatorName: nonEmpty(json['creator_name'] as String?),
      refund: rawRefund is Map<String, dynamic>
          ? OrderRefund.fromJson(rawRefund)
          : null,
    );
  }

  /// The order's stable, fan-safe code (server `id`, e.g. `ASN-…`).
  final String id;

  /// The order lifecycle state (server `status`, e.g. `paid`/`completed`).
  final String status;

  /// When the order was placed (server `created_at`, ISO-8601).
  final DateTime createdAt;

  /// The order's purchased lines (server `items`); never empty for a real
  /// order.
  final List<OrderItem> items;

  /// The pre-shipping goods subtotal in KRW won (server `subtotal`).
  final int subtotal;

  /// The shipping fee in KRW won (server `shipping_fee`); a mock `0` for now.
  final int shippingFee;

  /// The order total in KRW won (server `total` = subtotal + shipping_fee).
  final int total;

  /// The delivery snapshot for a goods order (server `shipping_address`); null
  /// for an order that needs no delivery.
  final OrderShipping? shippingAddress;

  /// The owning creator's display name (server `creator_name`); null when the
  /// product/creator is since-deleted.
  final String? creatorName;

  /// The latest refund request against this order (server `refund`); null when
  /// none was made.
  final OrderRefund? refund;

  /// The Korean label for [status] (mirrors the web order status map).
  ///
  /// Falls back to the raw [status] for an unknown value so a new server state
  /// still renders a label rather than nothing.
  String get statusLabel => switch (status) {
    'paid' => '결제완료',
    'shipping' => '배송중',
    'completed' => '완료',
    'cancelled' => '취소',
    'refunding' => '환불처리중',
    'refunded' => '환불완료',
    _ => status,
  };

  /// The order total formatted as `₩12,000` with thousands separators.
  String get totalLabel => '₩${formatThousands(total)}';

  /// A one-line summary of the order's contents (`제목 외 N건`).
  ///
  /// The first line's title, plus `외 N건` when the order has more than one
  /// line; an order with no lines (should not occur) reads as `주문`.
  String get summary {
    if (items.isEmpty) return '주문';
    final first = items.first.title;
    final extra = items.length - 1;
    return extra > 0 ? '$first 외 $extra건' : first;
  }
}
