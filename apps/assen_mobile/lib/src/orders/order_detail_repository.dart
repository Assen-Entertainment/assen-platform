import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/orders/order.dart';
import 'package:assen_mobile/src/orders/orders_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Thrown when `GET /api/orders/{id}` returns 404 (unknown or not-owned order).
///
/// A typed marker so the 주문 상세 screen can render a dedicated "주문을 찾을 수 없어요"
/// state rather than the generic retry error — the server 404s an id the fan
/// does not own (owner-scoped), so this doubles as the not-authorised-for-this
/// -order signal.
class OrderNotFoundException implements Exception {
  /// Creates the not-found marker.
  const OrderNotFoundException();

  @override
  String toString() => 'OrderNotFoundException';
}

/// Fetches a single order's full detail (incl. the delivery snapshot) for its
/// owner.
///
/// Kept separate from [OrdersRepository] (the paginated list): the detail
/// endpoint returns a richer, owner-scoped `OrderDetailOut` — including the
/// shipping-address PII the list deliberately omits (ASS-291 A-3). Reuses the
/// [Order] model, which already parses `shipping_address`. A 401 reuses
/// [OrdersAuthRequiredException] (signed out); a 404 becomes
/// [OrderNotFoundException]; other transport errors propagate.
class OrderDetailRepository {
  /// Creates a repository backed by [_dio].
  const OrderDetailRepository(this._dio);

  final Dio _dio;

  /// Loads one order via `GET /api/orders/{orderId}` (owner auth required).
  Future<Order> fetchOrder(String orderId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/orders/$orderId',
      );
      return Order.fromJson(response.data ?? const <String, dynamic>{});
    } on DioException catch (error) {
      final status = error.response?.statusCode;
      if (status == 401) throw const OrdersAuthRequiredException();
      if (status == 404) throw const OrderNotFoundException();
      rethrow;
    }
  }
}

/// Provides the [OrderDetailRepository] bound to the configured [dioProvider].
///
/// Overridden with a fake in widget tests so the 주문 상세 screen can render a mock
/// order (or the 401/404 branches) without a network.
final orderDetailRepositoryProvider = Provider<OrderDetailRepository>(
  (ref) => OrderDetailRepository(ref.watch(dioProvider)),
);
