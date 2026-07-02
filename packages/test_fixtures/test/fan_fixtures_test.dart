import 'package:test/test.dart';
import 'package:test_fixtures/test_fixtures.dart';

void main() {
  group('Fixtures.fan', () {
    test('provides stable defaults', () {
      final fan = Fixtures.fan();
      expect(fan.id, 'fan-001');
      expect(fan.displayName, 'Hatsukoi Guest');
    });

    test('allows overrides', () {
      final fan = Fixtures.fan(id: 'fan-042', displayName: 'Aoi');
      expect(fan.id, 'fan-042');
      expect(fan.displayName, 'Aoi');
    });
  });
}
