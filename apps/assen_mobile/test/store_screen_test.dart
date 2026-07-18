// Contract + render tests for the store catalog: Product.fromDetail parses the
// full ProductOut shape (and fromBrief the lean search brief), and the screen
// renders the grid / empty / error states through a fake repository (no
// network).

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
  test('Product.fromDetail parses the full ProductOut shape', () {
    final product = Product.fromDetail(_productRow());
    expect(product.title, '한정 아크릴 스탠드');
    expect(product.typeLabel, '굿즈');
    expect(product.priceLabel, '₩18,000');
    expect(product.description, '고급 아크릴 굿즈입니다.');
    expect(product.options, ['A타입', 'B타입']);
    expect(product.stock, 100);
    expect(product.soldOut, isFalse);
    expect(product.mediaUrl, isNull); // empty media_url degrades to null
  });

  test('Product.fromDetail throws when any required field is missing', () {
    // The catalog shape demands the full ProductOut set; a dropped field is a
    // load error, not a silent blank.
    for (final key in const [
      'id',
      'type',
      'title',
      'price',
      'meta',
      'media_url',
      'description',
      'options',
      'sold_out',
      'locked',
    ]) {
      final row = _productRow()..remove(key);
      expect(
        () => Product.fromDetail(row),
        throwsA(isA<ArgumentError>()),
        reason: 'a missing "$key" must throw',
      );
    }
  });

  test('Product.fromDetail degrades the server-optional fields', () {
    // creator_*/stock/is_adult are server-optional, so a bare required-only row
    // still constructs with their defaults.
    final product = Product.fromDetail(const {
      'id': 'g2',
      'type': 'goods',
      'title': '스티커',
      'price': 3000,
      'meta': '',
      'media_url': '',
      'description': '',
      'options': <String>[],
      'sold_out': false,
      'locked': false,
    });
    expect(product.creatorId, isNull);
    expect(product.creatorName, '');
    expect(product.stock, isNull);
    expect(product.isAdult, isFalse);
    expect(product.options, isEmpty); // an empty options list is valid
  });

  test('Product.fromBrief parses the lean search brief', () {
    final product = Product.fromBrief(const {
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

  test('Product.fromBrief throws when any required field is missing', () {
    for (final key in const ['id', 'type', 'title', 'price', 'meta']) {
      final row = <String, dynamic>{
        'id': 'p1',
        'type': 'ticket',
        'title': '팬미팅 티켓',
        'price': 55000,
        'meta': '',
      }..remove(key);
      expect(
        () => Product.fromBrief(row),
        throwsA(isA<ArgumentError>()),
        reason: 'a missing "$key" must throw',
      );
    }
  });

  testWidgets('renders the catalog grid parsed from the server row', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(_FakeStoreRepository.data([Product.fromDetail(_productRow())])),
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
