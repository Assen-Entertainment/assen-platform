import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:assen_mobile/src/orders/order.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Thrown when `GET /api/orders` returns 401 (the caller is signed out).
///
/// A typed marker (not a generic error) so the 주문 내역 screen can branch to the
/// "로그인이 필요해요" state rather than the generic retry error. This is the common
/// path today: the app ships signed-out, so the fan orders endpoint (which
/// requires `fan_auth`) answers 401 until real login lands (E6 gate). Mirrors
/// the R8 notifications auth-required pattern.
class OrdersAuthRequiredException implements Exception {
  /// Creates the auth-required marker.
  const OrdersAuthRequiredException();

  @override
  String toString() => 'OrdersAuthRequiredException';
}

/// Fetches the signed-in fan's own orders from the backend.
///
/// A thin repository over [Dio] owning the endpoint path and the JSON→model
/// mapping so the controller/UI stay transport-agnostic. When the generated
/// `api_client` (P6) lands, this delegates to it instead of calling Dio.
class OrdersRepository {
  /// Creates a repository backed by [_dio].
  const OrdersRepository(this._dio);

  final Dio _dio;

  /// Loads the fan's orders via `GET /api/orders` (auth required).
  ///
  /// Maps the `OrderPage` envelope (`{items, next_cursor}`) into a list of
  /// [Order]s, newest first; only the first page is read here (cursor paging is
  /// a follow-up). A 401 is translated into an [OrdersAuthRequiredException] so
  /// the screen shows the login-required state; other transport errors
  /// propagate to the error state.
  ///
  /// The envelope is parsed strictly: the `items` array must be present (an
  /// empty array is the empty history), but a *missing* key is a contract
  /// violation and throws (an [ArgumentError] via [requireList]) rather than
  /// silently showing no orders.
  Future<List<Order>> fetchOrders() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/orders');
      final body = response.data ?? const <String, dynamic>{};
      final items = requireList(body, 'items');
      return items
          .map((item) => Order.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (error) {
      if (error.response?.statusCode == 401) {
        throw const OrdersAuthRequiredException();
      }
      rethrow;
    }
  }
}

/// Provides the [OrdersRepository] bound to the configured [dioProvider].
///
/// Overridden with a fake in widget tests so the screen can render mock orders
/// (or the 401 branch) without a network.
final ordersRepositoryProvider = Provider<OrdersRepository>(
  (ref) => OrdersRepository(ref.watch(dioProvider)),
);
