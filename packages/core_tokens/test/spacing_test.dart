import 'package:core_tokens/core_tokens.dart';
import 'package:test/test.dart';

void main() {
  group('SpacingTokens', () {
    test('step 4 resolves to the 16px token value', () {
      expect(SpacingTokens.ofStep(4), 16);
    });

    test('step 0 resolves to zero', () {
      expect(SpacingTokens.ofStep(0), 0);
    });

    test('negative step is rejected', () {
      expect(() => SpacingTokens.ofStep(-1), throwsArgumentError);
    });
  });
}
