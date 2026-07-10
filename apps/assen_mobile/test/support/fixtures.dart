// Canonical app-model fixtures for the mobile tests.
//
// Thin wrappers that parse `test_fixtures`' backend-shaped JSON
// (`DomainFixtures`) into the app view models, so a test seeds a real
// `Creator`/`Post`/`Product`/… from one source instead of an inline map. The
// JSON literals live in the shared `test_fixtures` package (pure Dart, no app
// dependency); these builders bind them to the app types.

import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/membership/tier.dart';
import 'package:assen_mobile/src/mypage/fan_me.dart';
import 'package:assen_mobile/src/notifications/app_notification.dart';
import 'package:assen_mobile/src/orders/order.dart';
import 'package:assen_mobile/src/post/comment.dart';
import 'package:assen_mobile/src/post/post.dart';
import 'package:assen_mobile/src/search/search_result.dart';
import 'package:assen_mobile/src/store/product.dart';
import 'package:assen_mobile/src/studio/studio_stats.dart';
import 'package:test_fixtures/test_fixtures.dart';

/// A canonical [Creator]. Set [blocked] to exercise the profile block state.
Creator creatorFixture({String handle = 'mio', bool blocked = false}) =>
    Creator.fromJson(DomainFixtures.creator(handle: handle, blocked: blocked));

/// A canonical feed/detail [Post].
Post postFixture() => Post.fromJson(DomainFixtures.post());

/// A canonical post [Comment].
Comment commentFixture() => Comment.fromJson(DomainFixtures.comment());

/// A canonical full-detail [Product] (catalog / detail).
Product productFixture() => Product.fromDetail(DomainFixtures.productDetail());

/// A canonical lean search-brief [Product].
Product productBriefFixture() =>
    Product.fromBrief(DomainFixtures.productBrief());

/// A canonical [Order] (one item, no refund).
Order orderFixture() => Order.fromJson(DomainFixtures.order());

/// A canonical [AppNotification].
AppNotification notificationFixture() =>
    AppNotification.fromJson(DomainFixtures.notification());

/// A canonical membership [Tier]. Set [featured] false for a plain (badge-less)
/// tier.
Tier tierFixture({bool featured = true}) =>
    Tier.fromJson(DomainFixtures.tier(featured: featured));

/// A canonical [FanMe] identity summary.
FanMe fanMeFixture() => FanMe.fromJson(DomainFixtures.fanMe());

/// A canonical [StudioStats] dashboard summary.
StudioStats studioStatsFixture() =>
    StudioStats.fromJson(DomainFixtures.studioStats());

/// A canonical [SearchResult] (one creator + one product).
SearchResult searchResultFixture() =>
    SearchResult.fromJson(DomainFixtures.searchResult());
