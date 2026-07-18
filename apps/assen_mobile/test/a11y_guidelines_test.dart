// Automated accessibility-guideline coverage for the primary screens (R10,
// ASS-249; expanded R11 3→13 screens): every tappable element clears the
// Material 48dp / iOS 44pt hit-area floor and carries a label, and body text
// meets the contrast ratio. Each screen renders from a shared in-memory fake
// (test/support/fakes.dart) seeded with the canonical fixtures
// (test/support/fixtures.dart → test_fixtures' DomainFixtures); the fixture
// image URLs are empty, so the models map them to null and the screens skip
// building any cached-media/avatar image widget — nothing touches the network.
//
// The final group exercises CachedMedia's success-only image label (F1)
// directly through its `imageBuilder` (buildLoadedImage), so the labelled path
// is covered without a network fetch.

import 'dart:convert';

import 'package:assen_mobile/src/common/cached_media.dart';
import 'package:assen_mobile/src/creator/creator_repository.dart';
import 'package:assen_mobile/src/creator/creator_screen.dart';
import 'package:assen_mobile/src/discovery/discovery_repository.dart';
import 'package:assen_mobile/src/discovery/discovery_screen.dart';
import 'package:assen_mobile/src/feed/feed_repository.dart';
import 'package:assen_mobile/src/feed/feed_screen.dart';
import 'package:assen_mobile/src/membership/membership_repository.dart';
import 'package:assen_mobile/src/membership/membership_section.dart';
import 'package:assen_mobile/src/mypage/mypage_repository.dart';
import 'package:assen_mobile/src/mypage/mypage_screen.dart';
import 'package:assen_mobile/src/notifications/notifications_repository.dart';
import 'package:assen_mobile/src/notifications/notifications_screen.dart';
import 'package:assen_mobile/src/orders/orders_repository.dart';
import 'package:assen_mobile/src/orders/orders_screen.dart';
import 'package:assen_mobile/src/post/post_repository.dart';
import 'package:assen_mobile/src/post/post_screen.dart';
import 'package:assen_mobile/src/search/search_repository.dart';
import 'package:assen_mobile/src/search/search_screen.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:assen_mobile/src/settings/settings_screen.dart';
import 'package:assen_mobile/src/store/product_screen.dart';
import 'package:assen_mobile/src/store/store_repository.dart';
import 'package:assen_mobile/src/store/store_screen.dart';
import 'package:assen_mobile/src/studio/studio_repository.dart';
import 'package:assen_mobile/src/studio/studio_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

import 'support/fakes.dart';
import 'support/fixtures.dart';

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
  // One parameterized screen a11y case: a name, the provider overrides that
  // feed it fixture data, and the screen under test. The record type is
  // inferred (Riverpod's override type is not publicly nameable).
  final cases = [
    (
      name: 'discovery',
      overrides: [
        discoveryRepositoryProvider.overrideWithValue(
          FakeDiscoveryRepository([creatorFixture()]),
        ),
      ],
      screen: const DiscoveryScreen(),
    ),
    (
      name: 'feed',
      overrides: [
        feedRepositoryProvider.overrideWithValue(
          FakeFeedRepository([postFixture()]),
        ),
      ],
      screen: const FeedScreen(),
    ),
    (
      name: 'store',
      overrides: [
        storeRepositoryProvider.overrideWithValue(
          FakeStoreRepository([productFixture()]),
        ),
      ],
      screen: const StoreScreen(),
    ),
    (
      name: 'creator profile',
      overrides: [
        creatorRepositoryProvider.overrideWithValue(
          FakeCreatorRepository(creatorFixture()),
        ),
        membershipRepositoryProvider.overrideWithValue(
          FakeMembershipRepository([tierFixture()]),
        ),
      ],
      screen: const CreatorScreen(handle: 'mio'),
    ),
    (
      name: 'product detail',
      overrides: [
        storeRepositoryProvider.overrideWithValue(
          FakeStoreRepository(const [], product: productFixture()),
        ),
      ],
      screen: const ProductScreen(productId: 'g1'),
    ),
    (
      name: 'post detail',
      overrides: [
        postRepositoryProvider.overrideWithValue(
          FakePostRepository(postFixture(), comments: [commentFixture()]),
        ),
      ],
      screen: const PostScreen(postId: 'p1'),
    ),
    (
      name: 'notifications',
      overrides: [
        notificationsRepositoryProvider.overrideWithValue(
          FakeNotificationsRepository([notificationFixture()]),
        ),
      ],
      screen: const NotificationsScreen(),
    ),
    (
      name: 'orders',
      overrides: [
        ordersRepositoryProvider.overrideWithValue(
          FakeOrdersRepository([orderFixture()]),
        ),
      ],
      screen: const OrdersScreen(),
    ),
    (
      name: 'mypage',
      overrides: [
        myPageRepositoryProvider.overrideWithValue(
          FakeMyPageRepository(fanMeFixture()),
        ),
      ],
      screen: const MyPageScreen(),
    ),
    (
      name: 'settings',
      overrides: [
        settingsRepositoryProvider.overrideWithValue(
          FakeSettingsRepository(fanMeFixture()),
        ),
      ],
      screen: const SettingsScreen(),
    ),
    (
      name: 'studio',
      overrides: [
        studioRepositoryProvider.overrideWithValue(
          FakeStudioRepository(studioStatsFixture()),
        ),
      ],
      screen: const StudioScreen(),
    ),
    (
      name: 'membership section',
      overrides: [
        membershipRepositoryProvider.overrideWithValue(
          // A plain (non-featured) tier: the featured "추천" pastel badge is an
          // AssenBadge (ui_kit) contrast matter tracked separately, out of
          // scope for this screen-level a11y sweep.
          FakeMembershipRepository([tierFixture(featured: false)]),
        ),
      ],
      // Hosted in a Scaffold so the section header renders on the theme's
      // opaque background (a bare transparent host makes the contrast check
      // see alpha-0 behind the text).
      screen: const Scaffold(
        body: SingleChildScrollView(
          child: MembershipSection(creatorId: 'c1'),
        ),
      ),
    ),
  ];

  group('screen a11y guidelines', () {
    for (final testCase in cases) {
      testWidgets('${testCase.name} clears tap-target + label + contrast', (
        tester,
      ) async {
        final handle = tester.ensureSemantics();
        await tester.pumpWidget(
          ProviderScope(
            overrides: testCase.overrides,
            child: _app(testCase.screen),
          ),
        );
        await tester.pump();
        await tester.pump();
        await _expectA11y(tester);
        handle.dispose();
      });
    }

    // Search reaches its results state only after a debounced query, so it is
    // driven separately: type a term, let the 300ms debounce fire, then assert.
    testWidgets('search results clear tap-target + label + contrast', (
      tester,
    ) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            searchRepositoryProvider.overrideWithValue(
              FakeSearchRepository(searchResultFixture()),
            ),
          ],
          child: _app(const SearchScreen()),
        ),
      );
      await tester.pump();
      await tester.enterText(find.byType(TextField), '미오');
      // Past the debounce window, then let the fake resolve + the list build.
      await tester.pump(const Duration(milliseconds: 350));
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
