import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:operator_app/safety/operator_safety_providers.dart';
import 'package:operator_app/safety/operator_safety_repository.dart';
import 'package:operator_app/screens/operator_reports_screen.dart';
import 'package:ui_kit/ui_kit.dart';

Future<void> _pump(WidgetTester tester, {SafetyViewerRole? role}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        if (role != null) safetyViewerRoleProvider.overrideWithValue(role),
      ],
      child: MaterialApp(
        theme: AssenTheme.light(),
        home: const OperatorReportsScreen(),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

/// Switches the status-bucket segment, then opens the report with [title].
Future<void> _openReport(
  WidgetTester tester,
  String title, {
  String? bucket,
}) async {
  if (bucket != null) {
    await tester.tap(find.text(bucket));
    await tester.pumpAndSettle();
  }
  await tester.tap(find.text(title));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('lists reports for the selected bucket with classification '
      'badges and counts', (tester) async {
    await _pump(tester);

    expect(find.text('신고 처리'), findsOneWidget);
    // Status buckets carry their counts (received 1 / reviewing+actioned 2 /
    // closed 1) — summary fields any operator may triage.
    expect(find.text('접수 1'), findsOneWidget);
    expect(find.text('처리중 2'), findsOneWidget);
    expect(find.text('종료 1'), findsOneWidget);
    expect(find.text('사적 연락 시도 신고'), findsOneWidget);
    expect(find.text('높음'), findsOneWidget);
    expect(find.text('접수'), findsOneWidget);
    expect(find.textContaining('모든 상태 변경은 감사 로그'), findsOneWidget);
  });

  testWidgets('switching buckets shows the matching reports', (tester) async {
    await _pump(tester);

    await tester.tap(find.text('처리중 2'));
    await tester.pumpAndSettle();

    expect(find.text('촬영 규칙 위반 신고'), findsOneWidget); // reviewing
    expect(find.text('환불 분쟁 신고'), findsOneWidget); // actioned
    expect(find.text('사적 연락 시도 신고'), findsNothing); // received bucket hidden
  });

  testWidgets('advancing a report moves it to the next handling status', (
    tester,
  ) async {
    await _pump(tester); // operator+ may advance status
    await _openReport(tester, '사적 연락 시도 신고');

    // received → the first transition is 검토 시작.
    expect(find.text('검토 시작'), findsOneWidget);
    await tester.tap(find.text('검토 시작'));
    await tester.pumpAndSettle();

    // Now reviewing: the detail reflects 검토중 and offers the next step.
    expect(find.text('검토중'), findsWidgets);
    expect(find.text('조치 완료'), findsOneWidget);
    expect(find.text('검토 시작'), findsNothing);
  });

  testWidgets('a manager blocks the target and the card shows it', (
    tester,
  ) async {
    await _pump(tester, role: SafetyViewerRole.manager);
    await _openReport(tester, '사적 연락 시도 신고');

    await tester.tap(find.text('차단 / 위험 플래그'));
    await tester.pumpAndSettle();

    // Submit with the default closed scope/reason codes (hard block).
    await tester.tap(find.widgetWithText(FilledButton, '차단'));
    await tester.pumpAndSettle();

    // The block is surfaced on the report card behind the dialog.
    expect(find.text('차단됨'), findsOneWidget);
  });

  testWidgets('an operator sees the detail fields redacted and no manager '
      'actions', (tester) async {
    await _pump(tester, role: SafetyViewerRole.operator);
    await _openReport(tester, '사적 연락 시도 신고');

    // Reporter, target, and narrative are all redacted for an operator.
    expect(find.text('[redacted]'), findsNWidgets(3));
    expect(find.text('행사 종료 후 사적 연락처를 반복적으로 요구함.'), findsNothing);
    // Manager-only actions are hidden; status transition stays available.
    expect(find.widgetWithText(TextButton, '차단 / 위험 플래그'), findsNothing);
    expect(find.widgetWithText(TextButton, '종료'), findsNothing);
    expect(find.text('검토 시작'), findsOneWidget);
  });

  testWidgets(
    'an operator also sees a closed report resolution note redacted',
    (
      tester,
    ) async {
      await _pump(tester, role: SafetyViewerRole.operator);
      await _openReport(tester, '사기·부정 이용 신고', bucket: '종료 1');

      // reporter + target + narrative + 처리 메모 (closed report) = 4 fields.
      expect(find.text('[redacted]'), findsNWidgets(4));
      expect(find.text('쿠폰 부정 사용 정황 확인.'), findsNothing); // narrative
      expect(find.text('예약 기능 제한 처리 완료.'), findsNothing); // resolution note
    },
  );

  testWidgets('a closed report exposes no handling actions (terminal)', (
    tester,
  ) async {
    await _pump(tester, role: SafetyViewerRole.manager);
    await _openReport(tester, '사기·부정 이용 신고', bucket: '종료 1');

    expect(find.widgetWithText(TextButton, '닫기'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, '검토 시작'), findsNothing);
    expect(find.widgetWithText(FilledButton, '조치 완료'), findsNothing);
    expect(find.widgetWithText(TextButton, '종료'), findsNothing);
    expect(find.widgetWithText(TextButton, '차단 / 위험 플래그'), findsNothing);
  });

  testWidgets('a manager resolves an actioned report', (tester) async {
    await _pump(tester, role: SafetyViewerRole.manager);
    await _openReport(tester, '환불 분쟁 신고', bucket: '처리중 2');

    // 종료 is offered only once a report is actioned.
    expect(find.widgetWithText(TextButton, '종료'), findsOneWidget);
    await tester.tap(find.widgetWithText(TextButton, '종료'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), '환불 완료 확인');
    await tester.tap(find.widgetWithText(FilledButton, '종료'));
    await tester.pumpAndSettle();

    expect(find.text('신고를 종료했습니다.'), findsOneWidget);
  });
}
