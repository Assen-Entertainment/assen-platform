// Widget tests for AssenStepIndicator (가입·예약 플로우 점형). Renders completed,
// current and upcoming nodes with optional labels. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenStepIndicator', () {
    testWidgets('renders the step labels', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenStepIndicator(
            count: 4,
            currentStep: 1,
            labels: const ['약관', '통신사', '번호', 'OTP'],
          ),
        ),
      );
      expect(find.text('통신사'), findsOneWidget);
    });

    testWidgets('shows a check on completed steps', (tester) async {
      await tester.pumpWidget(
        _host(const AssenStepIndicator(count: 3, currentStep: 2)),
      );
      // Steps 0 and 1 are completed → two check glyphs.
      expect(find.byIcon(Icons.check), findsNWidgets(2));
    });
  });

  goldenTest(
    'step indicator matches the approved baseline',
    fileName: 'step_indicator',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'mid-flow',
          child: SizedBox(
            width: 320,
            child: AssenStepIndicator(
              count: 4,
              currentStep: 2,
              labels: const ['약관', '통신사', '번호', 'OTP'],
            ),
          ),
        ),
      ],
    ),
  );
}
