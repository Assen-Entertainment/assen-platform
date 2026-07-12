// Render tests for the 주문 상세 (order detail) screen: a 401 shows the login
// prompt, a 404 shows the not-found state, and a loaded order renders the
// contents, price total and the owner-only delivery snapshot. No network.

import 'package:assen_mobile/src/orders/order.dart';
import 'package:assen_mobile/src/orders/order_detail_repository.dart';
import 'package:assen_mobile/src/orders/order_detail_screen.dart';
import 'package:assen_mobile/src/orders/orders_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in: returns a fixed order, or the 401/404 errors.
class _FakeOrderDetailRepository implements OrderDetailRepository {
  _FakeOrderDetailRepository(Order order)
    : _order = order,
      _notFound = false;
  _FakeOrderDetailRepository.authRequired()
    : _order = null,
      _notFound = false;
  _FakeOrderDetailRepository.notFound() : _order = null, _notFound = true;

  final Order? _order;
  final bool _notFound;

  @override
  Future<Order> fetchOrder(String orderId) async {
    if (_notFound) throw const OrderNotFoundException();
    final order = _order;
    if (order == null) throw const OrdersAuthRequiredException();
    return order;
  }
}

Order _fixtureOrder() => Order(
  id: 'ORD-1',
  status: 'paid',
  createdAt: DateTime(2026, 7, 10),
  items: const [
    OrderItem(
      title: '아크릴 스탠드',
      type: 'goods',
      option: 'A타입',
      price: 15000,
      qty: 2,
    ),
  ],
  subtotal: 30000,
  shippingFee: 3000,
  total: 33000,
  shippingAddress: const OrderShipping(
    recipientName: '김민지',
    recipientPhone: '010-1234-5678',
    postalCode: '04524',
    address1: '서울시 중구',
    address2: '101호',
  ),
);

Widget _host(OrderDetailRepository repository) => ProviderScope(
  overrides: [orderDetailRepositoryProvider.overrideWithValue(repository)],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: const OrderDetailScreen(orderId: 'ORD-1'),
  ),
);

void main() {
  testWidgets('a 401 shows the login-required empty state', (tester) async {
    await tester.pumpWidget(
      _host(_FakeOrderDetailRepository.authRequired()),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('로그인이 필요해요'), findsOneWidget);
  });

  testWidgets('a 404 shows the not-found state', (tester) async {
    await tester.pumpWidget(_host(_FakeOrderDetailRepository.notFound()));
    await tester.pump();
    await tester.pump();

    expect(find.text('주문을 찾을 수 없어요'), findsOneWidget);
  });

  testWidgets('renders the breakdown, total and delivery snapshot', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(400, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_host(_FakeOrderDetailRepository(_fixtureOrder())));
    await tester.pump();
    await tester.pump();

    expect(find.text('아크릴 스탠드'), findsOneWidget);
    expect(find.text('₩33,000'), findsOneWidget); // total row
    expect(find.text('김민지 · 010-1234-5678'), findsOneWidget); // delivery
  });
}
