// Shared in-memory repository fakes for the mobile tests.
//
// Each fake `implements` its concrete repository and returns fixed data (from
// `fixtures.dart`) without a socket, so any test — screen render, a11y, router
// — can override the matching `*RepositoryProvider` with one line instead of
// re-declaring a `_Fake*Repository`. Feature tests that need a specific
// failure/auth-required variant keep their own local fake; these cover the
// common "loaded data" path shared across the suite.

import 'package:assen_mobile/src/creator/creator_repository.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/discovery/discovery_repository.dart';
import 'package:assen_mobile/src/feed/feed_repository.dart';
import 'package:assen_mobile/src/membership/membership_repository.dart';
import 'package:assen_mobile/src/membership/tier.dart';
import 'package:assen_mobile/src/mypage/fan_me.dart';
import 'package:assen_mobile/src/mypage/mypage_repository.dart';
import 'package:assen_mobile/src/notifications/app_notification.dart';
import 'package:assen_mobile/src/notifications/notifications_repository.dart';
import 'package:assen_mobile/src/orders/order.dart';
import 'package:assen_mobile/src/orders/orders_repository.dart';
import 'package:assen_mobile/src/post/comment.dart';
import 'package:assen_mobile/src/post/post.dart';
import 'package:assen_mobile/src/post/post_repository.dart';
import 'package:assen_mobile/src/search/search_repository.dart';
import 'package:assen_mobile/src/search/search_result.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:assen_mobile/src/store/product.dart';
import 'package:assen_mobile/src/store/store_repository.dart';
import 'package:assen_mobile/src/studio/studio_repository.dart';
import 'package:assen_mobile/src/studio/studio_stats.dart';

/// Returns a fixed creator list for the discovery feed.
class FakeDiscoveryRepository implements DiscoveryRepository {
  FakeDiscoveryRepository(this.creators);
  final List<Creator> creators;
  @override
  Future<List<Creator>> fetchCreators() async => creators;
}

/// Returns a fixed post list for the global feed.
class FakeFeedRepository implements FeedRepository {
  FakeFeedRepository(this.posts);
  final List<Post> posts;
  @override
  Future<List<Post>> fetchFeed() async => posts;
}

/// Returns a fixed catalog and, optionally, a single product detail.
class FakeStoreRepository implements StoreRepository {
  FakeStoreRepository(this.products, {this.product});
  final List<Product> products;
  final Product? product;
  @override
  Future<List<Product>> fetchProducts() async => products;
  @override
  Future<Product> fetchProduct(String productId) async =>
      product ?? (throw UnimplementedError());
}

/// Returns a fixed creator profile for any handle.
class FakeCreatorRepository implements CreatorRepository {
  FakeCreatorRepository(this.creator);
  final Creator creator;
  @override
  Future<Creator> fetchCreator(String handle) async => creator;
  @override
  Future<FollowState> setFollow(
    String handle, {
    required bool following,
  }) async => (following: following, followers: creator.followers);
}

/// Returns a fixed post and comment thread for any id.
class FakePostRepository implements PostRepository {
  FakePostRepository(this.post, {this.comments = const []});
  final Post post;
  final List<Comment> comments;
  @override
  Future<Post> fetchPost(String postId) async => post;
  @override
  Future<List<Comment>> fetchComments(String postId) async => comments;
  @override
  Future<LikeState> setLike(String postId, {required bool liked}) async =>
      (liked: liked, likeCount: post.likeCount);
  @override
  Future<Comment> addComment(String postId, String body) async => Comment(
    id: 'fake-comment',
    postId: postId,
    author: '나',
    body: body,
    createdAt: DateTime(2026, 7, 11),
  );
}

/// Returns a fixed order history.
class FakeOrdersRepository implements OrdersRepository {
  FakeOrdersRepository(this.orders);
  final List<Order> orders;
  @override
  Future<List<Order>> fetchOrders() async => orders;
}

/// Returns a fixed notification feed.
class FakeNotificationsRepository implements NotificationsRepository {
  FakeNotificationsRepository(this.items);
  final List<AppNotification> items;
  @override
  Future<List<AppNotification>> fetchNotifications() async => items;
  @override
  Future<AppNotification> markRead(String id) async {
    final match = items.firstWhere(
      (n) => n.id == id,
      orElse: () => AppNotification(
        id: id,
        kind: '',
        title: '',
        createdAt: DateTime(2026),
      ),
    );
    return match.copyWith(read: true);
  }

  @override
  Future<int> markAllRead() async => items.where((n) => !n.read).length;
}

/// Returns a fixed identity summary for the 마이 tab.
class FakeMyPageRepository implements MyPageRepository {
  FakeMyPageRepository(this.me);
  final FanMe me;
  @override
  Future<FanMe> fetchMe() async => me;
}

/// Returns a fixed identity for 설정; edit/verify actions are not exercised.
class FakeSettingsRepository implements SettingsRepository {
  FakeSettingsRepository(this.me);
  final FanMe me;
  @override
  Future<FanMe> fetchMe() async => me;
  @override
  Future<FanMe> updateNickname(String nickname) async =>
      throw UnimplementedError();
  @override
  Future<VerifyResult> verifyAdult() async => throw UnimplementedError();
}

/// Returns fixed studio dashboard counts.
class FakeStudioRepository implements StudioRepository {
  FakeStudioRepository(this.stats);
  final StudioStats stats;
  @override
  Future<StudioStats> fetchStats() async => stats;
}

/// Returns a fixed tier list for any creator.
class FakeMembershipRepository implements MembershipRepository {
  FakeMembershipRepository(this.tiers);
  final List<Tier> tiers;
  @override
  Future<List<Tier>> fetchTiers(String creatorId) async => tiers;
}

/// Returns a fixed search result for any query.
class FakeSearchRepository implements SearchRepository {
  FakeSearchRepository(this.result);
  final SearchResult result;
  @override
  Future<SearchResult> search(String query) async => result;
}
