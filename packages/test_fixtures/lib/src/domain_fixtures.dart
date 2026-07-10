/// Canonical backend-shaped JSON builders for the Assen domain.
///
/// The mobile screen tests each re-declared the same server-shaped map literals
/// (a post row, a product row, a creator row …) inline. [DomainFixtures]
/// centralises those literals as one seeded, override-friendly source so a
/// contract shape lives in exactly one place. The builders return plain
/// `Map<String, Object?>` — the raw JSON a screen's `Model.fromJson` parses —
/// so this package stays pure Dart and depends on no app types (the app depends
/// on `test_fixtures` as a dev dependency, never the reverse). App tests wrap
/// these with their own model constructors (see `test/support/fixtures.dart`).
///
/// Every default is fixed (no randomness, no clock reads) so equality-by-value
/// and golden assertions stay reproducible; pass an argument to vary one field.
library;

/// Deterministic, backend-shaped JSON map builders for the domain models.
abstract final class DomainFixtures {
  /// A default ISO-8601 timestamp used where a row needs a `created_at`.
  static const String defaultCreatedAt = '2026-07-01T00:00:00Z';

  /// A `CreatorOut` row. Image URLs default to empty (→ null in the model), so
  /// the built creator never triggers a network image in a widget test.
  static Map<String, Object?> creator({
    String id = 'c1',
    String handle = 'mio',
    String name = '미오',
    String category = '버추얼',
    String avatarUrl = '',
    String bio = '오늘도 방송 보러 와줘서 고마워요!',
    String coverUrl = '',
    String accentColor = '',
    bool verified = true,
    int followers = 1200,
    int posts = 34,
    bool blocked = false,
  }) {
    return {
      'id': id,
      'handle': handle,
      'name': name,
      'category': category,
      'avatar_url': avatarUrl,
      'bio': bio,
      'cover_url': coverUrl,
      'accent_color': accentColor,
      'verified': verified,
      'followers': followers,
      'posts': posts,
      'blocked': blocked,
    };
  }

  /// A `PostOut` row (feed / post detail).
  static Map<String, Object?> post({
    String id = 'p1',
    String creatorId = 'c1',
    String creatorName = '미오',
    String creatorHandle = 'mio',
    bool verified = true,
    String body = '오늘 방송 고마웠어요!',
    String mediaUrl = '',
    int likeCount = 128,
    int commentCount = 16,
    bool liked = false,
    bool isAdult = false,
    String createdAt = defaultCreatedAt,
  }) {
    return {
      'id': id,
      'creator_id': creatorId,
      'creator_name': creatorName,
      'creator_handle': creatorHandle,
      'verified': verified,
      'body': body,
      'media_url': mediaUrl,
      'like_count': likeCount,
      'comment_count': commentCount,
      'liked': liked,
      'is_adult': isAdult,
      'created_at': createdAt,
    };
  }

  /// A `CommentOut` row (post detail comment thread).
  static Map<String, Object?> comment({
    String id = 'cm1',
    String postId = 'p1',
    String author = '팬01',
    String body = '최고예요!',
    String createdAt = defaultCreatedAt,
  }) {
    return {
      'id': id,
      'post_id': postId,
      'author': author,
      'body': body,
      'created_at': createdAt,
    };
  }

  /// A full `ProductOut` row (catalog / product detail). Media defaults to
  /// empty (→ null) so no network image loads in a widget test.
  static Map<String, Object?> productDetail({
    String id = 'g1',
    String type = 'goods',
    String title = '한정 아크릴 스탠드',
    int price = 18000,
    String meta = '선착순 100개',
    String mediaUrl = '',
    String description = '고급 아크릴 굿즈입니다.',
    List<String> options = const ['A타입', 'B타입'],
    int? stock = 100,
    bool soldOut = false,
    bool locked = false,
    bool isAdult = false,
  }) {
    return {
      'id': id,
      'type': type,
      'title': title,
      'price': price,
      'meta': meta,
      'media_url': mediaUrl,
      'description': description,
      'options': options,
      'stock': stock,
      'sold_out': soldOut,
      'locked': locked,
      'is_adult': isAdult,
    };
  }

  /// A lean `ProductBrief` row (search result product).
  static Map<String, Object?> productBrief({
    String id = 'g1',
    String type = 'ticket',
    String title = '팬미팅 티켓',
    int price = 55000,
    String meta = '',
  }) {
    return {
      'id': id,
      'type': type,
      'title': title,
      'price': price,
      'meta': meta,
    };
  }

  /// An `OrderOut` row (order history). One item, no refund by default.
  static Map<String, Object?> order({
    String id = 'ASN-ABC123',
    String status = 'completed',
    String createdAt = defaultCreatedAt,
    List<Map<String, Object?>>? items,
    int subtotal = 12000,
    int total = 12000,
    String creatorName = '미오',
  }) {
    return {
      'id': id,
      'status': status,
      'created_at': createdAt,
      'items':
          items ??
          const [
            {
              'product_id': 'p1',
              'title': '봄 굿즈 세트',
              'type': 'goods',
              'option': 'M',
              'price': 12000,
              'qty': 1,
            },
          ],
      'subtotal': subtotal,
      'shipping': 0,
      'shipping_fee': 0,
      'total': total,
      'creator_name': creatorName,
    };
  }

  /// A `NotificationOut` row (알림 feed).
  static Map<String, Object?> notification({
    String id = 'n1',
    String kind = 'order',
    String title = '주문이 접수되었어요',
    String href = '/orders/1',
    bool read = false,
    String createdAt = defaultCreatedAt,
  }) {
    return {
      'id': id,
      'kind': kind,
      'title': title,
      'href': href,
      'read': read,
      'created_at': createdAt,
    };
  }

  /// A `TierOut` row (membership section).
  static Map<String, Object?> tier({
    String id = 't1',
    String creatorId = 'c1',
    String name = '하츠코이',
    int price = 9900,
    String period = '월',
    List<String> benefits = const ['멤버 전용 포스트', '월간 라이브'],
    String badge = '',
    bool featured = true,
    int sortOrder = 0,
  }) {
    return {
      'id': id,
      'creator_id': creatorId,
      'name': name,
      'price': price,
      'period': period,
      'benefits': benefits,
      'badge': badge,
      'featured': featured,
      'sort_order': sortOrder,
    };
  }

  /// A `FanMeOut` row (마이 / 설정 identity).
  static Map<String, Object?> fanMe({
    String id = 'fan1',
    String nickname = '하츠코이',
    String role = 'fan',
    String handle = '',
    String avatarUrl = '',
    bool adultVerified = false,
    String kycStatus = 'unverified',
  }) {
    return {
      'id': id,
      'nickname': nickname,
      'role': role,
      'handle': handle,
      'avatar_url': avatarUrl,
      'adult_verified': adultVerified,
      'kyc_status': kycStatus,
    };
  }

  /// A `StudioStatsOut` row (스튜디오 dashboard).
  static Map<String, Object?> studioStats({
    int followers = 1200,
    int posts = 34,
    int products = 12,
    int productsSelling = 8,
    int orders = 56,
    int subscribers = 42,
  }) {
    return {
      'followers': followers,
      'posts': posts,
      'products': products,
      'products_selling': productsSelling,
      'orders': orders,
      'subscribers': subscribers,
    };
  }

  /// A `SearchOut` envelope with the given [creators]/[products] rows.
  static Map<String, Object?> searchResult({
    List<Map<String, Object?>>? creators,
    List<Map<String, Object?>>? products,
  }) {
    return {
      'creators': creators ?? [creator()],
      'products': products ?? [productBrief()],
    };
  }
}
