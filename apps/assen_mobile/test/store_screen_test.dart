// Contract + render tests for the store catalog: Product.fromJson parses the
// full ProductOut shape, and the screen renders the grid / empty / error states
// through a fake repository (no network).

import 'package:assen_mobile/src/store/product.dart';
import 'package:assen_mobile/src/store/store_repository.dart';
import 'package:assen_mobile/src/store/store_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A store repository stand-in returning fixed products or throwing.
class _FakeStoreRepository implements StoreRepository {
  _FakeStoreRepository.data(List<Product> products)
    : _products = products,
      _error = null;
  _FakeStoreRepository.error() : _products = null, _error = Exception('boom');

  final List<Product>? _products;
  final Exception? _error;

  @override
  Future<List<Product>> fetchProducts() async {
    final error = _error;
    if (error != null) throw error;
    return _products!;
  }

  @override
  Future<Product> fetchProduct(String productId) async =>
      throw UnimplementedError();
}

Map<String, dynamic> _productRow() => {
  'id': 'g1',
  'creator_id': 'c1',
  'creator_name': '미오',
  'creator_handle': 'mio',
  'type': 'goods',
  'title': '한정 아크릴 스탠드',
  'price': 18000,
  'meta': '선착순 100개',
  'media_url': '',
  'description': '고급 아크릴 굿즈입니다.',
  'options': ['A타입', 'B타입'],
  'stock': 100,
  'sold_out': false,
  'locked': false,
  'is_adult': false,
};

Widget _host(StoreRepository repo) => ProviderScope(
  overrides: [storeRepositoryProvider.overrideWithValue(repo)],
  child: MaterialApp(theme: AssenTheme.light(), home: const StoreScreen()),
);

void main() {
  test('Product.fromJson parses the full ProductOut shape', () {
    final product = Product.fromJson(_productRow());
    expect(product.title, '한정 아크릴 스탠드');
    expect(product.typeLabel, '굿즈');
    expect(product.priceLabel, '₩18,000');
    expect(product.description, '고급 아크릴 굿즈입니다.');
    expect(product.options, ['A타입', 'B타입']);
    expect(product.stock, 100);
    expect(product.soldOut, isFalse);
    expect(product.mediaUrl, isNull); // empty media_url degrades to null
  });

  test('Product.fromJson still parses a lean search brief', () {
    final product = Product.fromJson(const {
      'id': 'p1',
      'type': 'ticket',
      'title': '팬미팅 티켓',
      'price': 55000,
      'meta': '',
    });
    expect(product.title, '팬미팅 티켓');
    expect(product.description, ''); // extras degrade to defaults
    expect(product.options, isEmpty);
    expect(product.stock, isNull);
  });

  testWidgets('renders the catalog grid parsed from the server row', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(_FakeStoreRepository.data([Product.fromJson(_productRow())])),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('한정 아크릴 스탠드'), findsOneWidget);
    expect(find.text('₩18,000'), findsOneWidget);
    expect(find.text('굿즈'), findsOneWidget); // type tag
  });

  testWidgets('shows the empty state for an empty catalog', (tester) async {
    await tester.pumpWidget(_host(_FakeStoreRepository.data(const [])));
    await tester.pump();
    await tester.pump();

    expect(find.text('아직 상품이 없어요'), findsOneWidget);
  });

  testWidgets('shows the error state on failure', (tester) async {
    await tester.pumpWidget(_host(_FakeStoreRepository.error()));
    await tester.pump();
    await tester.pump();

    expect(find.text('불러오지 못했어요'), findsOneWidget);
  });
}
