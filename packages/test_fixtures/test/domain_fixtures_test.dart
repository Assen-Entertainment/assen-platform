import 'package:test/test.dart';
import 'package:test_fixtures/test_fixtures.dart';

void main() {
  group('DomainFixtures', () {
    test('creator carries the CreatorOut required keys with defaults', () {
      final row = DomainFixtures.creator();
      expect(row['id'], 'c1');
      expect(row['handle'], 'mio');
      expect(row['name'], '미오');
      // Image URLs default empty so no network image loads in a widget test.
      expect(row['avatar_url'], '');
      expect(row['cover_url'], '');
    });

    test('post/order/notification rows expose created_at', () {
      expect(DomainFixtures.post()['created_at'], isNotNull);
      expect(DomainFixtures.order()['created_at'], isNotNull);
      expect(DomainFixtures.notification()['created_at'], isNotNull);
    });

    test('productDetail carries the full ProductOut shape', () {
      final row = DomainFixtures.productDetail();
      expect(row['type'], 'goods');
      expect(row['title'], '한정 아크릴 스탠드');
      expect(row['options'], isA<List<String>>());
      expect(row['sold_out'], isFalse);
    });

    test('overrides replace a single field, defaults hold the rest', () {
      final row = DomainFixtures.creator(handle: 'aoi', followers: 9);
      expect(row['handle'], 'aoi');
      expect(row['followers'], 9);
      expect(row['id'], 'c1'); // untouched default
    });

    test('searchResult nests creator + product rows', () {
      final row = DomainFixtures.searchResult();
      expect(row['creators'], isA<List<Map<String, Object?>>>());
      expect(row['products'], isA<List<Map<String, Object?>>>());
    });

    test('studioStats and fanMe expose their required keys', () {
      final stats = DomainFixtures.studioStats();
      expect(stats.keys, containsAll(['followers', 'products_selling']));
      final me = DomainFixtures.fanMe();
      expect(me.keys, containsAll(['id', 'nickname', 'role']));
    });
  });
}
