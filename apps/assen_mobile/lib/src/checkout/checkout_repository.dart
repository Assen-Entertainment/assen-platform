import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/orders/order.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Thrown when placing an order returns 401 (the caller is signed out).
class CheckoutAuthRequiredException implements Exception {
  /// Creates the auth-required marker.
  const CheckoutAuthRequiredException();

  @override
  String toString() => 'CheckoutAuthRequiredException';
}

/// Thrown when the (mock) payment rail is not open — the server's fail-closed
/// `require_payment_available()` head-guard rejects the order before any side
/// effect. The 결제 screen shows a "준비 중" notice rather than a hard error.
class PaymentUnavailableException implements Exception {
  /// Creates the payment-unavailable marker.
  const PaymentUnavailableException();

  @override
  String toString() => 'PaymentUnavailableException';
}

/// Thrown when the server rejects the order with a displayable reason (422/404):
/// a missing/partial delivery address, a free item routed to paid checkout, a
/// sold-out/unorderable listing, a blocked creator, or an unknown product. The
/// server's human-facing `detail` copy is surfaced inline.
class CheckoutRejectedException implements Exception {
  /// Creates a rejection carrying the server's [message].
  const CheckoutRejectedException(this.message);

  /// The human-facing rejection reason (server `detail`).
  final String message;

  @override
  String toString() => 'CheckoutRejectedException($message)';
}

/// A delivery address for a physical (goods) order — required for `type=goods`.
///
/// Mirrors the backend `ShippingIn` fields; [address2] (detail) is optional.
class ShippingInput {
  /// Creates a delivery address input.
  const ShippingInput({
    required this.recipientName,
    required this.recipientPhone,
    required this.postalCode,
    required this.address1,
    this.address2 = '',
  });

  /// The recipient's name.
  final String recipientName;

  /// The recipient's phone.
  final String recipientPhone;

  /// The delivery postal code.
  final String postalCode;

  /// The first address line.
  final String address1;

  /// The optional detail address line.
  final String address2;

  /// Whether the required fields (all but [address2]) are non-empty.
  bool get isComplete =>
      recipientName.trim().isNotEmpty &&
      recipientPhone.trim().isNotEmpty &&
      postalCode.trim().isNotEmpty &&
      address1.trim().isNotEmpty;

  /// The `ShippingIn` request body.
  Map<String, dynamic> toJson() => {
    'recipient_name': recipientName,
    'recipient_phone': recipientPhone,
    'postal_code': postalCode,
    'address1': address1,
    'address2': address2,
  };
}

/// Places (mock) orders and reports whether the payment rail is open.
///
/// A thin repository over [Dio] owning `GET /api/capabilities` (the gate flag)
/// and `POST /api/orders` (place order) plus the JSON↔model mapping. No card
/// data ever passes through — the mock records a `paid` order without moving
/// money (대표·PG 게이트). When the generated `api_client` (P6) lands this
/// delegates to it instead of Dio.
class CheckoutRepository {
  /// Creates a repository backed by [_dio].
  const CheckoutRepository(this._dio);

  final Dio _dio;

  /// Whether the (mock) payment rail is currently open (`payment_available`).
  ///
  /// Read from `GET /api/capabilities` so the UI can fail closed — hiding the
  /// pay action behind a "준비 중" notice when the gate is off — instead of
  /// letting a doomed POST reach the server's head-guard.
  Future<bool> paymentAvailable() async {
    final response = await _dio.get<Map<String, dynamic>>('/api/capabilities');
    final body = response.data ?? const <String, dynamic>{};
    return body['payment_available'] as bool? ?? false;
  }

  /// Places a mock order for one product via `POST /api/orders`.
  ///
  /// Returns the created [Order] (from the owner-scoped `OrderDetailOut`). A
  /// 401 becomes [CheckoutAuthRequiredException]; a 422/404 with a server
  /// `detail` becomes [CheckoutRejectedException] (carrying that copy); any
  /// other non-2xx is treated as the payment rail being unavailable
  /// ([PaymentUnavailableException]) so a gate-closed race degrades to the
  /// "준비 중" notice rather than a raw error.
  Future<Order> placeOrder({
    required String productId,
    required int qty,
    String option = '',
    ShippingInput? shipping,
    String? idempotencyKey,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/orders',
        data: <String, dynamic>{
          'product_id': productId,
          'qty': qty,
          if (option.isNotEmpty) 'option': option,
          if (shipping != null) 'shipping': shipping.toJson(),
          'idempotency_key': ?idempotencyKey,
        },
      );
      return Order.fromJson(response.data ?? const <String, dynamic>{});
    } on DioException catch (error) {
      final status = error.response?.statusCode;
      if (status == 401) throw const CheckoutAuthRequiredException();
      if (status == 422 || status == 404) {
        throw CheckoutRejectedException(
          _detail(error) ?? '주문을 완료하지 못했어요.',
        );
      }
      throw const PaymentUnavailableException();
    }
  }

  /// Extracts the server's human-facing `detail` from an error body, if any.
  String? _detail(DioException error) {
    final data = error.response?.data;
    if (data is Map && data['detail'] is String) {
      return data['detail'] as String;
    }
    return null;
  }
}

/// Provides the [CheckoutRepository] bound to the [dioProvider].
///
/// Overridden with a fake in widget tests so the 결제 screen can exercise the
/// place-order flow (and the gate/rejection branches) without a network.
final checkoutRepositoryProvider = Provider<CheckoutRepository>(
  (ref) => CheckoutRepository(ref.watch(dioProvider)),
);
