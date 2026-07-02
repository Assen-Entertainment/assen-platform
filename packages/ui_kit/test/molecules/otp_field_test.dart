// Widget tests for AssenOtpField (입력중 / 완료 / 오류). Renders one cell per digit
// and fires onCompleted at full length. Pixel golden skipped pending #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenOtpField', () {
    testWidgets('reports digits as they are entered', (tester) async {
      String? code;
      await tester.pumpWidget(
        _host(AssenOtpField(onChanged: (v) => code = v)),
      );
      await tester.enterText(find.byType(TextField), '123');
      expect(code, '123');
    });

    testWidgets('fires onCompleted at full length', (tester) async {
      String? completed;
      await tester.pumpWidget(
        _host(
          AssenOtpField(onChanged: (_) {}, onCompleted: (v) => completed = v),
        ),
      );
      await tester.enterText(find.byType(TextField), '654321');
      expect(completed, '654321');
    });

    testWidgets('shows the error message in the error state', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenOtpField(
            onChanged: (_) {},
            status: AssenOtpStatus.error,
            errorText: '인증번호가 일치하지 않습니다',
          ),
        ),
      );
      expect(find.text('인증번호가 일치하지 않습니다'), findsOneWidget);
    });
  });

  goldenTest(
    'otp field matches the approved baseline',
    fileName: 'otp_field',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'entering',
          child: SizedBox(
            width: 280,
            child: AssenOtpField(onChanged: (_) {}),
          ),
        ),
      ],
    ),
  );
}
