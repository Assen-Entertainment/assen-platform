import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/refreshable_async_notifier.dart';
import 'package:assen_mobile/src/orders/order.dart';
import 'package:assen_mobile/src/orders/order_detail_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// The family provider type returned by `AsyncNotifierProvider.family` lives in
// riverpod's `misc` library, not the default export; it is imported here so the
// provider can carry the explicit type the workspace ruleset requires.
import 'package:flutter_riverpod/misc.dart' show AsyncNotifierProviderFamily;

/// Drives one order's detail async lifecycle, keyed by order id.
///
/// A family [AsyncNotifier] (one instance per order) so the 주문 상세 screen
/// renders loading/error/data from a single value and can re-run its fetch via
/// [refresh] (retry). The order-id argument is delivered by the family
/// (Riverpod 3.x) and read back in [build]. A signed-out caller surfaces as an
/// OrdersAuthRequiredException, an unknown id as an OrderNotFoundException.
class OrderDetailController extends AsyncNotifier<Order>
    with RefreshableAsyncNotifier<Order> {
  /// Creates a controller for the order identified by [orderId].
  OrderDetailController(this.orderId);

  /// The id of the order this controller loads.
  final String orderId;

  @override
  Future<Order> build() =>
      ref.watch(orderDetailRepositoryProvider).fetchOrder(orderId);

  @override
  Future<Order> fetch() =>
      ref.read(orderDetailRepositoryProvider).fetchOrder(orderId);
}

/// Exposes each order's detail [AsyncValue], keyed by order id.
final AsyncNotifierProviderFamily<OrderDetailController, Order, String>
orderDetailControllerProvider =
    AsyncNotifierProvider.family<OrderDetailController, Order, String>(
      OrderDetailController.new,
      retry: noRetry,
    );
