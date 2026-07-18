// Contract + render tests for the 주문 내역 tab: Order.fromJson parses the server
// OrderOut shape, a 401 (OrdersAuthRequiredException) shows the login empty
// state, an authenticated history renders its order cards, and an empty history
// shows the empty state. Read-only surface — no placement/cancel/refund action
// is offered or exercised. No network.

import 'package:assen_mobile/src/orders/order.dart';
import 'package:assen_mobile/src/orders/orders_repository.dart';
import 'package:assen_mobile/src/orders/orders_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in returning a fixed history or the auth-required error.
class _FakeOrdersRepository implements OrdersRepository {
  _FakeOrdersRepository.items(List<Order> items)
    : _items = items,
      _error = null;
  _FakeOrdersRepository.authRequired()
    : _items = null,
      _error = const OrdersAuthRequiredException();

  final List<Order>? _items;
  final Exception? _error;

  @override
  Future<List<Order>> fetchOrders() async {
    final error = _error;
    if (error != null) throw error;
    return _items!;
  }
}

Widget _host(OrdersRepository repository) => ProviderScope(
  overrides: [ordersRepositoryProvider.overrideWithValue(repository)],
  child: MaterialApp(theme: AssenTheme.light(), home: const OrdersScreen()),
);

void main() {
  test('Order.fromJson parses the OrderOut shape', () {
    final order = Order.fromJson(const {
      'id': 'ASN-ABC123',
      'status': 'paid',
      'created_at': '2026-07-06T09:00:00Z',
      'items': [
        {
          'product_id': 'p1',
          'title': '봄 굿즈 세트',
          'type': 'goods',
          'option': 'M',
          'price': 12000,
          'qty': 1,
        },
      ],
      'subtotal': 12000,
      'shipping': 0,
      'shipping_fee': 0,
      'total': 12000,
      'creator_name': '호시노',
    });
    expect(order.id, 'ASN-ABC123');
    expect(order.statusLabel, '결제완료');
    expect(order.total, 12000);
    expect(order.totalLabel, '₩12,000');
    expect(order.summary, '봄 굿즈 세트');
    expect(order.items.single.qty, 1);
    expect(order.refund, isNull);
  });

  test('Order.fromJson throws on a missing required field', () {
    // A missing `created_at` violates the OrderOut contract (field drift), so
    // the model throws rather than rendering an undated order.
    expect(
      () => Order.fromJson(const {
        'id': 'ASN-1',
        'status': 'paid',
        'items': <dynamic>[],
        'subtotal': 0,
        'shipping': 0,
        'shipping_fee': 0,
        'total': 0,
      }),
      throwsA(isA<ArgumentError>()),
    );
  });

  test('Order.fromJson throws when the required shipping field is absent', () {
    // The server sends `shipping` and `shipping_fee` as duplicate required
    // fields (same value); a missing `shipping` is contract drift and must
    // throw rather than silently pass on `shipping_fee` alone.
    expect(
      () => Order.fromJson(const {
        'id': 'ASN-3',
        'status': 'paid',
        'created_at': '2026-07-06T09:00:00Z',
        'items': <dynamic>[],
        'subtotal': 0,
        'shipping_fee': 0,
        'total': 0,
      }),
      throwsA(isA<ArgumentError>()),
    );
  });

  test('Order.summary condenses multiple lines', () {
    final order = Order.fromJson(const {
      'id': 'ASN-2',
      'status': 'completed',
      'created_at': '2026-07-06T09:00:00Z',
      'items': [
        {'title': '체키', 'type': 'goods', 'option': '', 'price': 5000, 'qty': 2},
        {
          'title': '스티커',
          'type': 'goods',
          'option': '',
          'price': 2000,
          'qty': 1,
        },
      ],
      'subtotal': 12000,
      'shipping': 0,
      'shipping_fee': 0,
      'total': 12000,
    });
    expect(order.summary, '체키 외 1건');
  });

  testWidgets('a 401 shows the login-required empty state', (tester) async {
    await tester.pumpWidget(_host(_FakeOrdersRepository.authRequired()));
    await tester.pump();
    await tester.pump();

    expect(find.text('로그인이 필요해요'), findsOneWidget);
    expect(find.text('로그인'), findsOneWidget); // the CTA
  });

  testWidgets('an authenticated history renders its orders', (tester) async {
    await tester.pumpWidget(
      _host(
        _FakeOrdersRepository.items([
          Order(
            id: 'ASN-1',
            status: 'completed',
            createdAt: DateTime(2026, 7, 6),
            items: const [
              OrderItem(
                title: '체키',
                type: 'goods',
                option: '',
                price: 5000,
                qty: 2,
              ),
            ],
            subtotal: 10000,
            shippingFee: 0,
            total: 10000,
            refund: const OrderRefund(status: 'requested', reason: '단순 변심'),
          ),
        ]),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('체키'), findsOneWidget); // summary
    expect(find.text('완료'), findsOneWidget); // status badge label
    expect(find.text('₩10,000'), findsOneWidget); // total
    expect(find.text('환불 접수'), findsOneWidget); // refund badge
  });

  testWidgets('an empty history shows the empty state', (tester) async {
    await tester.pumpWidget(_host(_FakeOrdersRepository.items(const [])));
    await tester.pump();
    await tester.pump();

    expect(find.text('주문 내역이 없어요'), findsOneWidget);
  });
}
