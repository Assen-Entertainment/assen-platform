import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

void main() {
  group('AssenWindowSize', () {
    test('maps Material 3 breakpoint boundaries', () {
      expect(AssenWindowSize.fromWidth(599), AssenWindowSize.compact);
      expect(AssenWindowSize.fromWidth(600), AssenWindowSize.medium);
      expect(AssenWindowSize.fromWidth(839), AssenWindowSize.medium);
      expect(AssenWindowSize.fromWidth(840), AssenWindowSize.expanded);
    });
  });
}
