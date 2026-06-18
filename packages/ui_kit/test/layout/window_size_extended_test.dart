import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void main() {
  group('AssenWindowSize large / extraLarge (un-collapsed)', () {
    test('fromWidth maps the large and extra-large boundaries', () {
      // The existing window_size_test pins <=840; these are the NEW boundaries.
      expect(AssenWindowSize.fromWidth(1199), AssenWindowSize.expanded);
      expect(AssenWindowSize.fromWidth(1200), AssenWindowSize.large);
      expect(AssenWindowSize.fromWidth(1599), AssenWindowSize.large);
      expect(AssenWindowSize.fromWidth(1600), AssenWindowSize.extraLarge);
      expect(AssenWindowSize.fromWidth(2560), AssenWindowSize.extraLarge);
    });

    test('atLeast compares by class order', () {
      expect(AssenWindowSize.large.atLeast(AssenWindowSize.expanded), isTrue);
      expect(
        AssenWindowSize.extraLarge.atLeast(AssenWindowSize.large),
        isTrue,
      );
      expect(
        AssenWindowSize.expanded.atLeast(AssenWindowSize.expanded),
        isTrue,
      );
      expect(AssenWindowSize.expanded.atLeast(AssenWindowSize.large), isFalse);
      expect(AssenWindowSize.compact.atLeast(AssenWindowSize.medium), isFalse);
    });

    test(
      'assenGridCrossAxisCount falls back large/XL to expanded by default',
      () {
        // 3-arg callers stay unchanged: large/XL inherit the expanded count.
        expect(
          assenGridCrossAxisCount(1300, compact: 2, medium: 3, expanded: 4),
          4,
        );
        expect(
          assenGridCrossAxisCount(1700, compact: 2, medium: 3, expanded: 4),
          4,
        );
      },
    );

    test('assenGridCrossAxisCount honours explicit large/XL counts', () {
      expect(
        assenGridCrossAxisCount(
          1300,
          compact: 2,
          medium: 3,
          expanded: 4,
          large: 5,
          extraLarge: 6,
        ),
        5,
      );
      expect(
        assenGridCrossAxisCount(
          1700,
          compact: 2,
          medium: 3,
          expanded: 4,
          large: 5,
          extraLarge: 6,
        ),
        6,
      );
      // extraLarge falls back to large when only large is given.
      expect(
        assenGridCrossAxisCount(
          1700,
          compact: 2,
          medium: 3,
          expanded: 4,
          large: 5,
        ),
        5,
      );
    });
  });
}
