// Render + place-order tests for the 결제 (checkout) screen: an open rail shows
// the summary + pay button, a closed rail shows the 준비 중 notice, a goods order
// shows the delivery form, and paying places the (mock) order and shows the
// confirmation. No network.

import 'package:assen_mobile/src/checkout/checkout_repository.dart';
import 'package:assen_mobile/src/checkout/checkout_screen.dart';
import 'package:assen_mobile/src/orders/order.dart';
import 'package:assen_mobile/src/store/product.dart';
import 'package:assen_mobile/src/store/store_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

import 'support/fakes.dart';

/// A checkout repository stand-in: reports the rail state and returns (or
/// rejects) a placed order, recording the shipping it was called with.
class _FakeCheckoutRepository implements CheckoutRepository {
  _FakeCheckoutRepository({this.paymentOpen = true, this.order});

  final bool paymentOpen;
  final Order? order;

  /// The shipping passed to the last [placeOrder] call, or null.
  ShippingInput? lastShipping;

  @override
  Future<bool> paymentAvailable() async => paymentOpen;

  @override
  Future<Order> placeOrder({
    required String productId,
    required int qty,
    String option = '',
    ShippingInput? shipping,
    String? idempotencyKey,
  }) async {
    lastShipping = shipping;
    return order!;
  }
}

Product _digital() =>
    const Product(id: 'p-9', type: 'digital', title: '디지털 화보', price: 5000);

Product _goods() =>
    const Product(id: 'p-8', type: 'goods', title: '아크릴 스탠드', price: 12000);

Order _order() => Order(
  id: 'ORD-9',
  status: 'paid',
  createdAt: DateTime(2026, 7, 12),
  items: const [
    OrderItem(
      title: '디지털 화보',
      type: 'digital',
      option: '',
      price: 5000,
      qty: 1,
    ),
  ],
  subtotal: 5000,
  shippingFee: 0,
  total: 5000,
);

Widget _host({
  required Product product,
  required CheckoutRepository checkout,
}) => ProviderScope(
  overrides: [
    storeRepositoryProvider.overrideWithValue(
      FakeStoreRepository(const [], product: product),
    ),
    checkoutRepositoryProvider.overrideWithValue(checkout),
  ],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: CheckoutScreen(productId: product.id),
  ),
);

void main() {
  testWidgets('an open rail shows the summary and pay button', (tester) async {
    await tester.pumpWidget(
      _host(product: _digital(), checkout: _FakeCheckoutRepository()),
    );
    await tester.pumpAndSettle();

    expect(find.text('디지털 화보'), findsOneWidget);
    expect(find.textContaining('결제하기'), findsOneWidget);
  });

  testWidgets('a closed rail shows the 준비 중 notice, no pay button', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        product: _digital(),
        checkout: _FakeCheckoutRepository(paymentOpen: false),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('준비 중'), findsWidgets);
    expect(find.textContaining('결제하기'), findsNothing);
  });

  testWidgets('a goods order shows the delivery form', (tester) async {
    tester.view.physicalSize = const Size(400, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _host(product: _goods(), checkout: _FakeCheckoutRepository()),
    );
    await tester.pumpAndSettle();

    expect(find.text('배송지'), findsOneWidget);
    expect(find.text('받는 분'), findsOneWidget);
  });

  testWidgets('paying places the order and shows the confirmation', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        product: _digital(),
        checkout: _FakeCheckoutRepository(order: _order()),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.textContaining('결제하기'));
    await tester.pumpAndSettle();

    expect(find.text('주문이 완료되었어요'), findsOneWidget);
    expect(find.textContaining('ORD-9'), findsOneWidget);
  });
}
