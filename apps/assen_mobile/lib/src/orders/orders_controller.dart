import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/orders/order.dart';
import 'package:assen_mobile/src/orders/orders_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Drives the 주문 내역 (orders) screen's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value
/// and can re-run the fetch via [refresh] (retry). A signed-out caller surfaces
/// as an [OrdersAuthRequiredException] in the error state, which the screen
/// maps to the "로그인이 필요해요" branch rather than a failure.
class OrdersController extends AsyncNotifier<List<Order>> {
  @override
  Future<List<Order>> build() {
    return ref.watch(ordersRepositoryProvider).fetchOrders();
  }

  /// Re-fetches the orders, surfacing a fresh loading then data/error state.
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => ref.read(ordersRepositoryProvider).fetchOrders(),
    );
  }
}

/// Exposes the fan's orders [AsyncValue] and its [OrdersController].
final ordersControllerProvider =
    AsyncNotifierProvider<OrdersController, List<Order>>(
      OrdersController.new,
      retry: noRetry,
    );
