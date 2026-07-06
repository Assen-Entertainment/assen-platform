// Contract + render tests for the search tab: Product/SearchResult.fromJson
// parse the server shapes, and the screen shows guidance → results → no-results
// through a fake repository (debounced, no network).

import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/search/product.dart';
import 'package:assen_mobile/src/search/search_repository.dart';
import 'package:assen_mobile/src/search/search_result.dart';
import 'package:assen_mobile/src/search/search_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// A repository stand-in returning a fixed result for any query.
class _FakeSearchRepository implements SearchRepository {
  _FakeSearchRepository(this._result);

  final SearchResult _result;

  @override
  Future<SearchResult> search(String query) async => _result;
}

Widget _host(SearchResult result) => ProviderScope(
  overrides: [
    searchRepositoryProvider.overrideWithValue(_FakeSearchRepository(result)),
  ],
  child: MaterialApp(theme: AssenTheme.light(), home: const SearchScreen()),
);

SearchResult _oneOfEach() => SearchResult(
  creators: [
    Creator.fromJson(const {
      'id': 'c1',
      'handle': 'mio',
      'name': '미오',
      'category': '버추얼',
      'avatar_url': '',
    }),
  ],
  products: [
    Product.fromJson(const {
      'id': 'p1',
      'type': 'goods',
      'title': '아크릴 스탠드',
      'price': 18000,
      'meta': '선착순',
    }),
  ],
);

void main() {
  test('Product.fromJson parses the ProductBrief shape', () {
    final product = Product.fromJson(const {
      'id': 'p1',
      'type': 'ticket',
      'title': '팬미팅 티켓',
      'price': 55000,
      'meta': '',
    });
    expect(product.title, '팬미팅 티켓');
    expect(product.typeLabel, '티켓');
    expect(product.priceLabel, '₩55,000');
    expect(product.meta, isNull); // empty meta degrades to null
  });

  test('SearchResult.fromJson splits creators and products', () {
    final result = SearchResult.fromJson(const {
      'creators': [
        {'id': 'c1', 'handle': 'mio', 'name': '미오'},
      ],
      'products': [
        {'id': 'p1', 'type': 'goods', 'title': '굿즈', 'price': 1000, 'meta': ''},
      ],
    });
    expect(result.creators, hasLength(1));
    expect(result.products, hasLength(1));
    expect(result.isEmpty, isFalse);
  });

  test('SearchResult.empty is empty', () {
    expect(const SearchResult.empty().isEmpty, isTrue);
  });

  testWidgets('shows guidance for an empty query', (tester) async {
    await tester.pumpWidget(_host(const SearchResult.empty()));
    await tester.pump();
    expect(find.text('무엇을 찾고 있나요?'), findsOneWidget);
  });

  testWidgets('shows creators and products after a debounced query', (
    tester,
  ) async {
    await tester.pumpWidget(_host(_oneOfEach()));
    await tester.pump();

    await tester.enterText(find.byType(TextField), 'mio');
    // Let the debounce fire, then resolve the fake future.
    await tester.pump(const Duration(milliseconds: 350));
    await tester.pump();

    expect(find.text('미오'), findsOneWidget);
    expect(find.text('아크릴 스탠드'), findsOneWidget);
    expect(find.text('₩18,000'), findsOneWidget);
  });

  testWidgets('shows the no-results empty state', (tester) async {
    await tester.pumpWidget(_host(const SearchResult.empty()));
    await tester.pump();

    await tester.enterText(find.byType(TextField), 'zzz');
    await tester.pump(const Duration(milliseconds: 350));
    await tester.pump();

    expect(find.text('결과가 없어요'), findsOneWidget);
  });
}
