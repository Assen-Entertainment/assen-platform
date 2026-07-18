// Render tests for the 상품 관리 (studio products) screen: a 401 shows the login
// prompt, a 403 the creator-only notice, and a loaded list renders each
// product's title, price, status and sold count. No network.

import 'package:assen_mobile/src/studio/studio_product.dart';
import 'package:assen_mobile/src/studio/studio_products_repository.dart';
import 'package:assen_mobile/src/studio/studio_products_screen.dart';
import 'package:assen_mobile/src/studio/studio_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in: returns a fixed product list, or the 401/403 errors.
class _FakeStudioProductsRepository implements StudioProductsRepository {
  _FakeStudioProductsRepository(List<StudioProduct> products)
    : _products = products,
      _owner = false;
  _FakeStudioProductsRepository.authRequired()
    : _products = null,
      _owner = false;
  _FakeStudioProductsRepository.ownerRequired()
    : _products = null,
      _owner = true;

  final List<StudioProduct>? _products;
  final bool _owner;

  @override
  Future<List<StudioProduct>> fetchProducts() async {
    if (_owner) throw const StudioOwnerRequiredException();
    final products = _products;
    if (products == null) throw const StudioAuthRequiredException();
    return products;
  }
}

const _product = StudioProduct(
  id: 'p-1',
  type: 'goods',
  title: '아크릴 키링',
  price: 8000,
  status: 'selling',
  soldOut: false,
  sold: 12,
  isAdult: false,
);

Widget _host(StudioProductsRepository repository) => ProviderScope(
  overrides: [
    studioProductsRepositoryProvider.overrideWithValue(repository),
  ],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: const StudioProductsScreen(),
  ),
);

void main() {
  testWidgets('a 401 shows the login-required empty state', (tester) async {
    await tester.pumpWidget(
      _host(_FakeStudioProductsRepository.authRequired()),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('로그인이 필요해요'), findsOneWidget);
  });

  testWidgets('a 403 shows the creator-only state', (tester) async {
    await tester.pumpWidget(
      _host(_FakeStudioProductsRepository.ownerRequired()),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('크리에이터 전용이에요'), findsOneWidget);
  });

  testWidgets('renders a product with its status and sold count', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(_FakeStudioProductsRepository(const [_product])),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('아크릴 키링'), findsOneWidget);
    expect(find.text('₩8,000'), findsOneWidget);
    expect(find.text('판매중'), findsOneWidget);
    expect(find.text('판매 12'), findsOneWidget);
  });
}
