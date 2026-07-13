// Render tests for the product detail: renders title / price / options with
// sold-out & locked badges, offers a 구매하기 CTA (→ checkout) for an orderable
// item, and a 404 surfaces the "없는 상품" state. Fake repository, no network.

import 'package:assen_mobile/src/store/product.dart';
import 'package:assen_mobile/src/store/product_screen.dart';
import 'package:assen_mobile/src/store/store_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A store repository stand-in returning a fixed product or a 404.
class _FakeStoreRepository implements StoreRepository {
  _FakeStoreRepository.data(Product product)
    : _product = product,
      _notFound = false;
  _FakeStoreRepository.notFound() : _product = null, _notFound = true;

  final Product? _product;
  final bool _notFound;

  @override
  Future<List<Product>> fetchProducts() async => throw UnimplementedError();

  @override
  Future<Product> fetchProduct(String productId) async {
    if (_notFound) throw ProductNotFoundException(productId);
    return _product!;
  }
}

Product _product({bool soldOut = false, bool locked = false}) =>
    Product.fromDetail({
      'id': 'g1',
      'type': 'goods',
      'title': '한정 아크릴 스탠드',
      'price': 18000,
      'meta': '',
      'media_url': '',
      'description': '고급 아크릴 굿즈입니다.',
      'options': const ['A타입', 'B타입'],
      'stock': 100,
      'sold_out': soldOut,
      'locked': locked,
      'is_adult': false,
    });

Widget _host(StoreRepository repo) => ProviderScope(
  overrides: [storeRepositoryProvider.overrideWithValue(repo)],
  child: MaterialApp(
    theme: AssenTheme.light(),
    home: const ProductScreen(productId: 'g1'),
  ),
);

void main() {
  testWidgets('renders the detail with a 구매하기 checkout CTA', (tester) async {
    await tester.pumpWidget(_host(_FakeStoreRepository.data(_product())));
    await tester.pump();
    await tester.pump();

    expect(find.text('한정 아크릴 스탠드'), findsOneWidget);
    expect(find.text('₩18,000'), findsOneWidget);
    expect(find.text('고급 아크릴 굿즈입니다.'), findsOneWidget);
    expect(find.text('A타입'), findsOneWidget); // option chip

    // An orderable item offers a 구매하기 CTA into the (mock) checkout; the old
    // browse-only "준비 중" notice is gone.
    expect(find.widgetWithText(AssenButton, '구매하기'), findsOneWidget);
    expect(
      find.text('지금은 상품을 둘러볼 수 있어요. 구매 기능은 준비 중입니다.'),
      findsNothing,
    );
  });

  testWidgets('shows the sold-out and locked badges', (tester) async {
    await tester.pumpWidget(
      _host(_FakeStoreRepository.data(_product(soldOut: true, locked: true))),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('품절'), findsOneWidget);
    expect(find.text('멤버십 전용'), findsOneWidget);
  });

  testWidgets('a 404 shows the unknown-product state', (tester) async {
    await tester.pumpWidget(_host(_FakeStoreRepository.notFound()));
    await tester.pump();
    await tester.pump();

    expect(find.text('없는 상품이에요'), findsOneWidget);
  });
}
