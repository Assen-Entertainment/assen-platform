// Automated accessibility-guideline coverage for the primary screens (R10,
// ASS-249): every tappable element clears the Material 48dp / iOS 44pt hit-area
// floor and carries a label, and body text meets the contrast ratio. Fake
// repositories feed server-shaped rows with empty image URLs; those empty
// strings map to null in the models (`nonEmpty`), so the screens skip building
// the cached-media/avatar image widgets entirely — nothing touches the network
// (no placeholder to degrade to; the widget simply is not created).
//
// The final group exercises CachedMedia's success-only image label (F1)
// directly through its `imageBuilder` (buildLoadedImage), so the labelled path
// is covered without a network fetch.

import 'dart:convert';

import 'package:assen_mobile/src/common/cached_media.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/discovery/discovery_repository.dart';
import 'package:assen_mobile/src/discovery/discovery_screen.dart';
import 'package:assen_mobile/src/feed/feed_repository.dart';
import 'package:assen_mobile/src/feed/feed_screen.dart';
import 'package:assen_mobile/src/post/post.dart';
import 'package:assen_mobile/src/store/product.dart';
import 'package:assen_mobile/src/store/store_repository.dart';
import 'package:assen_mobile/src/store/store_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

class _FakeDiscoveryRepository implements DiscoveryRepository {
  _FakeDiscoveryRepository(this._creators);

  final List<Creator> _creators;

  @override
  Future<List<Creator>> fetchCreators() async => _creators;
}

class _FakeFeedRepository implements FeedRepository {
  _FakeFeedRepository(this._posts);

  final List<Post> _posts;

  @override
  Future<List<Post>> fetchFeed() async => _posts;
}

class _FakeStoreRepository implements StoreRepository {
  _FakeStoreRepository(this._products);

  final List<Product> _products;

  @override
  Future<List<Product>> fetchProducts() async => _products;

  @override
  Future<Product> fetchProduct(String productId) async =>
      throw UnimplementedError();
}

Creator _creator() => Creator.fromJson(const {
  'id': 'c1',
  'handle': 'mio',
  'name': '미오',
  'category': '버추얼',
  'avatar_url': '',
  'verified': true,
  'followers': 12,
  'posts': 3,
});

Post _post() => Post.fromJson(const {
  'id': 'p1',
  'creator_id': 'c1',
  'creator_name': '미오',
  'creator_handle': 'mio',
  'verified': true,
  'body': '오늘 방송 고마웠어요!',
  'media_url': '',
  'like_count': 128,
  'comment_count': 16,
  'liked': false,
  'is_adult': false,
  'created_at': '2026-07-01T00:00:00Z',
});

Product _product() => Product.fromDetail(const {
  'id': 'g1',
  'type': 'goods',
  'title': '한정 아크릴 스탠드',
  'price': 18000,
  'meta': '선착순 100개',
  'media_url': '',
  'description': '고급 아크릴 굿즈입니다.',
  'options': <String>[],
  'sold_out': false,
  'locked': false,
});

Widget _app(Widget home) => MaterialApp(theme: AssenTheme.light(), home: home);

Future<void> _expectA11y(WidgetTester tester, {bool contrast = true}) async {
  await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
  await expectLater(tester, meetsGuideline(iOSTapTargetGuideline));
  await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
  if (contrast) {
    await expectLater(tester, meetsGuideline(textContrastGuideline));
  }
}

void main() {
  group('screen a11y guidelines', () {
    testWidgets('discovery clears tap-target + label + contrast', (
      tester,
    ) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            discoveryRepositoryProvider.overrideWithValue(
              _FakeDiscoveryRepository([_creator()]),
            ),
          ],
          child: _app(const DiscoveryScreen()),
        ),
      );
      await tester.pump();
      await tester.pump();
      await _expectA11y(tester);
      handle.dispose();
    });

    testWidgets('feed clears tap-target + label + contrast', (tester) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            feedRepositoryProvider.overrideWithValue(
              _FakeFeedRepository([_post()]),
            ),
          ],
          child: _app(const FeedScreen()),
        ),
      );
      await tester.pump();
      await tester.pump();
      await _expectA11y(tester);
      handle.dispose();
    });

    testWidgets('store clears tap-target + label + contrast', (tester) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            storeRepositoryProvider.overrideWithValue(
              _FakeStoreRepository([_product()]),
            ),
          ],
          child: _app(const StoreScreen()),
        ),
      );
      await tester.pump();
      await tester.pump();
      await _expectA11y(tester);
      handle.dispose();
    });
  });

  group('cached media image label rides only on a successful load', () {
    const label = '게시물 이미지';
    // A minimal valid 1x1 PNG so Image decodes locally, without any network.
    final pngBytes = base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4'
      '2mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
    );

    testWidgets('labels the loaded image via imageBuilder', (tester) async {
      final handle = tester.ensureSemantics();
      const media = CachedMedia(
        url: 'https://assen.test/a.jpg',
        semanticLabel: label,
      );
      await tester.pumpWidget(
        _app(
          Builder(
            builder: (context) =>
                media.buildLoadedImage(context, MemoryImage(pngBytes)),
          ),
        ),
      );
      expect(find.bySemanticsLabel(label), findsOneWidget);
      expect(
        tester.getSemantics(find.bySemanticsLabel(label)),
        isSemantics(label: label, isImage: true),
      );
      handle.dispose();
    });

    testWidgets('omits the label when semanticLabel is null', (tester) async {
      final handle = tester.ensureSemantics();
      const media = CachedMedia(url: 'https://assen.test/a.jpg');
      await tester.pumpWidget(
        _app(
          Builder(
            builder: (context) =>
                media.buildLoadedImage(context, MemoryImage(pngBytes)),
          ),
        ),
      );
      expect(find.bySemanticsLabel(label), findsNothing);
      handle.dispose();
    });

    testWidgets('cream fallback carries no image label before a load', (
      tester,
    ) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(
        _app(
          const CachedMedia(
            url: 'https://assen.test/never.jpg',
            semanticLabel: label,
          ),
        ),
      );
      // The first frame paints the cream placeholder (imageBuilder has not
      // run), so the image label must be absent — a broken/pending load is
      // never announced as the item.
      expect(find.bySemanticsLabel(label), findsNothing);
      handle.dispose();
    });
  });
}
